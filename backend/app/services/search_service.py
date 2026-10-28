"""Search service: full-text, semantic and hybrid retrieval."""
from __future__ import annotations

import time
from typing import List

from sqlalchemy.orm import Session

from app.core.config import settings
from app.embeddings import EmbeddingUnavailable
from app.models.search import SearchHistory
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.search.fulltext import FTSHit, search_fulltext
from app.search.hybrid import deduplicate_by_document, reciprocal_rank_fusion
from app.search.semantic import SemanticHit, search_semantic


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    async def search(self, request: SearchRequest) -> SearchResponse:
        started = time.perf_counter()
        notes: List[str] = []

        if not request.query.strip():
            return SearchResponse(
                results=[],
                total=0,
                query=request.query,
                mode=request.mode,
                response_time_ms=0,
                notes=["Empty query: enter at least one search term."],
            )

        document_ids = request.filters.document_ids if request.filters else None
        extensions = request.filters.extensions if request.filters else None

        if request.mode == "fulltext":
            results, total = self._run_fulltext(request, document_ids, extensions)
        elif request.mode == "semantic":
            results, total = self._run_semantic(request, document_ids, extensions, notes)
        else:
            results, total = self._run_hybrid(request, document_ids, extensions, notes)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._record_history(request, total, elapsed_ms)

        return SearchResponse(
            results=results,
            total=total,
            query=request.query,
            mode=request.mode,
            response_time_ms=elapsed_ms,
            notes=notes,
        )

    # -- individual modes -------------------------------------------------
    def _run_fulltext(self, request, document_ids, extensions):
        hits, total = search_fulltext(
            self.db,
            request.query,
            limit=request.limit,
            offset=request.offset,
            document_ids=document_ids,
            extensions=extensions,
        )
        results = [self._from_fts(hit) for hit in hits]
        results = self._limit_per_document(results, request.max_per_document)
        return results, total

    def _run_semantic(self, request, document_ids, extensions, notes):
        try:
            hits, total = search_semantic(
                self.db,
                request.query,
                limit=request.limit,
                offset=request.offset,
                document_ids=document_ids,
                extensions=extensions,
            )
        except EmbeddingUnavailable as exc:
            notes.append(f"Semantic search unavailable: {exc}")
            return [], 0

        results = [self._from_semantic(hit) for hit in hits]
        results = self._limit_per_document(results, request.max_per_document)
        return results, total

    def _run_hybrid(self, request, document_ids, extensions, notes):
        # Fetch a wider candidate pool for each retriever before fusing.
        pool = max(request.limit * 5, 50)

        fts_hits, _ = search_fulltext(
            self.db,
            request.query,
            limit=pool,
            offset=0,
            document_ids=document_ids,
            extensions=extensions,
        )

        semantic_hits: List[SemanticHit] = []
        try:
            semantic_hits, _ = search_semantic(
                self.db,
                request.query,
                limit=pool,
                offset=0,
                document_ids=document_ids,
                extensions=extensions,
            )
        except EmbeddingUnavailable as exc:
            notes.append(
                f"Hybrid fell back to full-text only because semantic search is unavailable: {exc}"
            )

        if not semantic_hits:
            results = [self._from_fts(hit) for hit in fts_hits]
            results = self._limit_per_document(results, request.max_per_document)
            return results[request.offset : request.offset + request.limit], len(results)

        fts_ranking = [h.chunk_id for h in fts_hits]
        semantic_ranking = [h.chunk_id for h in semantic_hits]

        fused = reciprocal_rank_fusion(
            [fts_ranking, semantic_ranking],
            k=60,
            weights=[request.fts_weight, request.semantic_weight],
        )

        chunk_lookup = {h.chunk_id: h for h in fts_hits}
        chunk_lookup.update({h.chunk_id: h for h in semantic_hits})
        chunk_to_document = {h.chunk_id: h.document_id for h in fts_hits}
        chunk_to_document.update({h.chunk_id: h.document_id for h in semantic_hits})

        fused = deduplicate_by_document(fused, chunk_to_document, request.max_per_document)
        total = len(fused)
        window = fused[request.offset : request.offset + request.limit]

        results = []
        for chunk_id, score in window:
            hit = chunk_lookup.get(chunk_id)
            if hit is None:
                continue
            results.append(self._from_fused(hit, score, chunk_lookup))
        return results, total

    # -- converters -------------------------------------------------------
    def _from_fts(self, hit: FTSHit) -> SearchResultItem:
        return SearchResultItem(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            document_name=hit.filename,
            extension=hit.extension,
            content=hit.content,
            snippet=hit.snippet,
            heading=hit.heading,
            score=hit.score,
            highlights=hit.highlights,
            match_type="fulltext",
            explanation=f"Keyword match on: {', '.join(hit.highlights)}"
            if hit.highlights
            else "Keyword match in document text.",
        )

    def _from_semantic(self, hit: SemanticHit) -> SearchResultItem:
        return SearchResultItem(
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            document_name=hit.filename,
            extension=hit.extension,
            content=hit.content,
            snippet=hit.snippet,
            page_number=hit.page_number,
            heading=hit.heading,
            score=round(hit.score, 4),
            highlights=[],
            match_type="semantic",
            explanation=f"Semantic similarity {hit.score:.3f} with the query.",
        )

    def _from_fused(self, hit, score: float, lookup: dict) -> SearchResultItem:
        if isinstance(hit, FTSHit):
            item = self._from_fts(hit)
            item.highlights = hit.highlights
            origin = "keyword and semantic retrieval"
        else:
            item = self._from_semantic(hit)  # type: ignore[arg-type]
            origin = "keyword and semantic retrieval"
        item.score = round(score, 6)
        item.match_type = "hybrid"
        item.explanation = f"Fused with Reciprocal Rank Fusion ({origin})."
        return item

    def _limit_per_document(self, results: List[SearchResultItem], cap: int):
        counts: dict[str, int] = {}
        kept = []
        for item in results:
            used = counts.get(item.document_id, 0)
            if used >= cap:
                continue
            counts[item.document_id] = used + 1
            kept.append(item)
        return kept

    def _record_history(self, request: SearchRequest, total: int, elapsed_ms: int):
        if not getattr(settings, "STORE_SEARCH_HISTORY", True):
            return
        try:
            self.db.add(
                SearchHistory(
                    query=request.query,
                    search_mode=request.mode,
                    result_count=total,
                    response_time_ms=elapsed_ms,
                )
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
