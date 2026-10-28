#!/usr/bin/env python
"""Reproducible retrieval benchmark for Local Knowledge Engine.

The script creates a throw-away SQLite database, indexes the synthetic corpus in
``sample_documents/``, runs a fixed set of queries with known relevant
documents, and reports document-level Precision@k, Recall@k, MRR, nDCG@k and
latency for full-text, semantic and hybrid search.

No numbers are hard-coded. Run it yourself:

    cd backend
    .venv/Scripts/python.exe ../scripts/benchmark.py --download-model

Semantic mode is skipped (and clearly reported) when sentence-transformers or
the embedding model is unavailable. ``--download-model`` is an explicit opt-in
because the model is fetched from Hugging Face the first time.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import platform
import statistics
import sqlite3
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SAMPLE_DIR = ROOT / "sample_documents"
sys.path.insert(0, str(BACKEND))

# Query -> relevant document filenames. Labels are exhaustive for this corpus.
QUERIES = [
    {
        "query": "Which port does the Atlas API listen on?",
        "relevant": ["atlas-handbook.md"],
    },
    {
        "query": "When are database backups taken?",
        "relevant": ["atlas-handbook.md"],
    },
    {
        "query": "How quickly must the primary on-call acknowledge a page?",
        "relevant": ["atlas-handbook.md"],
    },
    {
        "query": "What is Project Halyard?",
        "relevant": ["atlas-onboarding.txt"],
    },
    {
        "query": "How long do production access tokens last?",
        "relevant": ["atlas-security.md"],
    },
    {
        "query": "How often are encryption keys rotated?",
        "relevant": ["atlas-security.md"],
    },
    {
        "query": "What changed in version 2.3.0?",
        "relevant": ["atlas-release-notes.md"],
    },
    {
        "query": "How long are audit logs retained?",
        "relevant": ["atlas-faq.md"],
    },
    {
        "query": "What was the p95 latency in March 2026?",
        "relevant": ["atlas-service-metrics.csv"],
    },
    {
        "query": "What should I do when the primary database is unreachable during failover?",
        "relevant": ["atlas-database-runbook.html", "atlas-handbook.md"],
    },
    {
        "query": "Can I index a folder outside my home directory?",
        "relevant": ["atlas-faq.md"],
    },
    {
        "query": "Which formats were added in release 2.2.0?",
        "relevant": ["atlas-release-notes.md"],
    },
]


# -- metrics ---------------------------------------------------------------
def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return sum(1 for doc in ranked[:k] if doc in relevant) / k


def hit_rate_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if any(doc in relevant for doc in ranked[:k]) else 0.0


def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return sum(1 for doc in ranked[:k] if doc in relevant) / len(relevant)


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    for position, doc in enumerate(ranked, start=1):
        if doc in relevant:
            return 1.0 / position
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    dcg = sum(
        1.0 / math.log2(position + 1)
        for position, doc in enumerate(ranked[:k], start=1)
        if doc in relevant
    )
    ideal = sum(
        1.0 / math.log2(position + 1)
        for position in range(1, min(len(relevant), k) + 1)
    )
    return dcg / ideal if ideal else 0.0


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


# -- corpus ----------------------------------------------------------------
def prepare_database(work_dir: Path) -> Path:
    db_path = work_dir / "benchmark.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["ALLOWED_IMPORT_DIRS"] = str(SAMPLE_DIR)
    os.environ["ENABLE_SEMANTIC_SEARCH"] = "false"
    os.environ["ENABLE_AI_ASSISTANT"] = "false"
    os.environ["STORE_SEARCH_HISTORY"] = "false"
    return db_path


def index_corpus(db) -> tuple[int, int]:
    from app.indexing.pipeline import IndexingPipeline, sha256_file
    from app.models.document import Document

    files = sorted(SAMPLE_DIR.glob("atlas-*"))
    if not files:
        raise SystemExit(f"No sample documents found in {SAMPLE_DIR}")

    pipeline = IndexingPipeline(db)
    chunk_count = 0
    for path in files:
        document = Document(
            filename=path.name,
            original_path=str(path),
            file_hash=sha256_file(str(path)),
            file_size=path.stat().st_size,
            extension=path.suffix.lower(),
            parsing_status="pending",
            indexing_status="pending",
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        result = pipeline.index_document(document, compute_embeddings=False)
        if result.indexing_status != "completed":
            raise SystemExit(f"Indexing failed for {path.name}: {result.parsing_error}")
        chunk_count += result.chunk_count or 0
    return len(files), chunk_count


def build_embeddings(db, allow_download: bool, notes: list[str]) -> bool:
    from app.core.config import settings
    from app.embeddings import EmbeddingEngine, EmbeddingUnavailable
    from app.models.document import Document, DocumentChunk
    from app.search.semantic import store_embeddings

    engine = EmbeddingEngine.get_instance()
    settings.ENABLE_SEMANTIC_SEARCH = True
    try:
        engine.load_model(allow_download=allow_download)
    except EmbeddingUnavailable as exc:
        settings.ENABLE_SEMANTIC_SEARCH = False
        notes.append(f"Semantic mode skipped: {exc}")
        return False
    except Exception as exc:  # noqa: BLE001 - report, do not hide
        settings.ENABLE_SEMANTIC_SEARCH = False
        notes.append(f"Semantic mode skipped: cannot load embedding model: {exc}")
        return False
    total = 0
    for document in db.query(Document).all():
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        total += store_embeddings(db, document.id, chunks, engine)

    notes.append(
        f"Computed {total} embeddings with {engine.model_name} on {engine.device}."
    )
    return total > 0


# -- evaluation ------------------------------------------------------------
async def evaluate_mode(db, mode: str, limit: int, k: int) -> dict:
    from app.schemas.search import SearchRequest
    from app.services.search_service import SearchService

    service = SearchService(db)
    per_query = []
    latencies = []

    for item in QUERIES:
        request = SearchRequest(query=item["query"], mode=mode, limit=limit)
        # First call warms model/caches; the second call is measured.
        await service.search(request)
        started = time.perf_counter()
        response = await service.search(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        latencies.append(elapsed_ms)

        ranked_documents: list[str] = []
        for result in response.results:
            if result.document_name not in ranked_documents:
                ranked_documents.append(result.document_name)

        relevant = set(item["relevant"])
        per_query.append(
            {
                "query": item["query"],
                "relevant": sorted(relevant),
                "ranked_documents": ranked_documents,
                "precision_at_k": precision_at_k(ranked_documents, relevant, k),
                "precision_at_1": precision_at_k(ranked_documents, relevant, 1),
                "hit_rate_at_k": hit_rate_at_k(ranked_documents, relevant, k),
                "recall_at_k": recall_at_k(ranked_documents, relevant, k),
                "reciprocal_rank": reciprocal_rank(ranked_documents, relevant),
                "ndcg_at_k": ndcg_at_k(ranked_documents, relevant, k),
                "latency_ms": round(elapsed_ms, 3),
                "notes": response.notes,
            }
        )

    return {
        "mode": mode,
        "k": k,
        "queries": len(per_query),
        "precision_at_k": statistics.fmean(q["precision_at_k"] for q in per_query),
        "precision_at_1": statistics.fmean(q["precision_at_1"] for q in per_query),
        "hit_rate_at_k": statistics.fmean(q["hit_rate_at_k"] for q in per_query),
        "recall_at_k": statistics.fmean(q["recall_at_k"] for q in per_query),
        "mrr": statistics.fmean(q["reciprocal_rank"] for q in per_query),
        "ndcg_at_k": statistics.fmean(q["ndcg_at_k"] for q in per_query),
        "mean_latency_ms": statistics.fmean(latencies),
        "p95_latency_ms": percentile(latencies, 0.95),
        "per_query": per_query,
    }


def hardware_info() -> dict:
    info = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
    }
    try:
        import sentence_transformers

        info["sentence_transformers"] = sentence_transformers.__version__
    except ImportError:
        info["sentence_transformers"] = None
    try:
        import torch

        info["torch"] = torch.__version__
    except ImportError:
        info["torch"] = None
    return info


def print_markdown(result: dict, notes: list[str], corpus: dict) -> None:
    print("\n## Retrieval benchmark\n")
    print(f"Generated: `{result['generated_at']}`\n")
    print(
        f"Corpus: {corpus['documents']} documents / {corpus['chunks']} chunks · "
        f"{result['queries']} labelled queries · k={result['k']} · limit={result['limit']}"
    )
    print()
    print(
        "| Mode | P@1 | Hit@5 | Precision@5 | Recall@5 | MRR | nDCG@5 | Mean latency | p95 latency |"
    )
    print(
        "|------|-----|-------|-------------|----------|-----|--------|--------------|-------------|"
    )
    for mode in result["modes"]:
        print(
            f"| {mode['mode']} | {mode['precision_at_1']:.3f} | {mode['hit_rate_at_k']:.3f} | "
            f"{mode['precision_at_k']:.3f} | {mode['recall_at_k']:.3f} | "
            f"{mode['mrr']:.3f} | {mode['ndcg_at_k']:.3f} | {mode['mean_latency_ms']:.1f} ms | "
            f"{mode['p95_latency_ms']:.1f} ms |"
        )
    if notes:
        print("\nNotes:")
        for note in notes:
            print(f"- {note}")


async def run(args: argparse.Namespace) -> int:
    work_dir = Path(tempfile.mkdtemp(prefix="lke-benchmark-"))
    db_path = prepare_database(work_dir)

    # Import application modules only after DATABASE_URL is set.
    import app.models  # noqa: F401 - registers tables
    from app.database.base import Base, SessionLocal, engine
    from app.search.fts import ensure_fts_table

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    notes: list[str] = []
    try:
        ensure_fts_table(db)
        documents, chunks = index_corpus(db)
        corpus = {
            "documents": documents,
            "chunks": chunks,
            "path": str(SAMPLE_DIR),
        }

        semantic_ready = build_embeddings(db, args.download_model, notes)
        modes_to_run = ["fulltext"] + (["semantic", "hybrid"] if semantic_ready else [])

        results = []
        for mode in modes_to_run:
            result = await evaluate_mode(db, mode, args.limit, args.k)
            results.append(result)
            print(
                f"{mode}: P@{args.k}={result['precision_at_k']:.3f} "
                f"R@{args.k}={result['recall_at_k']:.3f} MRR={result['mrr']:.3f} "
                f"nDCG@{args.k}={result['ndcg_at_k']:.3f} "
                f"mean={result['mean_latency_ms']:.1f}ms",
                flush=True,
            )

        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "k": args.k,
            "limit": args.limit,
            "queries": len(QUERIES),
            "corpus": corpus,
            "database": str(db_path),
            "hardware": hardware_info(),
            "modes": results,
            "notes": notes,
        }

        print_markdown(payload, notes, corpus)
        if args.json:
            output = Path(args.json)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            print(f"\nJSON written to {output}")

        if args.fail_if_semantic_missing and not semantic_ready:
            return 2
        return 0
    finally:
        db.close()
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=5, help="cut-off for P@k/R@k/nDCG@k")
    parser.add_argument("--limit", type=int, default=10, help="results requested per query")
    parser.add_argument(
        "--download-model",
        action="store_true",
        help="allow the embedding model to download on first use",
    )
    parser.add_argument("--json", default=None, help="write full results as JSON")
    parser.add_argument(
        "--fail-if-semantic-missing",
        action="store_true",
        help="exit with status 2 if semantic mode could not run",
    )
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
