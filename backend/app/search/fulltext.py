"""Full-text search over SQLite FTS5."""
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.search.fts import (
    FTS_TABLE,
    build_fts_fallback_query,
    build_fts_query,
    ensure_fts_table,
)

SNIPPET_START = "\u0001"
SNIPPET_END = "\u0002"


@dataclass
class FTSHit:
    chunk_id: str
    document_id: str
    filename: str
    extension: str
    content: str
    snippet: str
    heading: Optional[str] = None
    score: float = 0.0
    highlights: List[str] = field(default_factory=list)


def search_fulltext(
    db: Session,
    query: str,
    limit: int = 20,
    offset: int = 0,
    document_ids: Optional[List[str]] = None,
    extensions: Optional[List[str]] = None,
) -> tuple[List[FTSHit], int]:
    """Run an FTS5 search. Returns (hits, total_matches)."""
    ensure_fts_table(db)

    match_expression = build_fts_query(query)
    if not match_expression:
        return [], 0

    where_clauses = [f"{FTS_TABLE} MATCH :match"]
    params: dict = {"match": match_expression, "limit": limit + 1, "offset": offset}
    # Note: document_id is UNINDEXED, filtering it in the same query is not
    # supported by FTS5 MATCH, so filters are applied afterwards.

    sql = f"""
        SELECT
            chunk_id,
            document_id,
            filename,
            extension,
            heading,
            snippet({FTS_TABLE}, 0, '{SNIPPET_START}', '{SNIPPET_END}', ' … ', 40) AS snip,
            bm25({FTS_TABLE}) AS rank,
            content
        FROM {FTS_TABLE}
        WHERE {' AND '.join(where_clauses)}
        ORDER BY rank
        LIMIT :limit OFFSET :offset
    """

    # Fetch a wider window when filters are requested so that filtering does
    # not silently drop results to zero.
    if document_ids or extensions:
        params["limit"] = max((limit + offset) * 10, 200)
        params["offset"] = 0

    try:
        rows = db.execute(text(sql), params).fetchall()
    except Exception:
        return [], 0

    # A strict AND across every term can miss natural-language questions.
    # Fall back to a broader OR query before giving up.
    if not rows:
        fallback = build_fts_fallback_query(query)
        if fallback and fallback != match_expression:
            params["match"] = fallback
            try:
                rows = db.execute(text(sql), params).fetchall()
            except Exception:
                return [], 0

    hits: List[FTSHit] = []
    document_filter = set(document_ids) if document_ids else None
    extension_filter = {e.lower() for e in extensions} if extensions else None
    for row in rows:
        if document_filter and row.document_id not in document_filter:
            continue
        if extension_filter and (row.extension or "").lower() not in extension_filter:
            continue

        snippet = row.snip or (row.content[:240] if row.content else "")
        snippet, highlights = _extract_highlights(snippet)

        hits.append(
            FTSHit(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                filename=row.filename,
                extension=row.extension or "",
                content=row.content or "",
                snippet=snippet,
                heading=row.heading or None,
                score=float(row.rank or 0.0),
                highlights=highlights,
            )
        )

    total = _count_matches(db, params["match"])
    if document_filter or extension_filter:
        # Filters are applied after FTS matching, so report the filtered count
        total = offset + len(hits)

    return hits[offset : offset + limit] if (document_filter or extension_filter) else hits[:limit], total


def _count_matches(db: Session, match_expression: str) -> int:
    try:
        row = db.execute(
            text(f"SELECT count(*) AS total FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH :match"),
            {"match": match_expression},
        ).fetchone()
        return int(row.total) if row else 0
    except Exception:
        return 0


def _extract_highlights(snippet: str) -> tuple[str, List[str]]:
    """Replace FTS5 highlight markers with plain text and collect terms."""
    highlights = []
    plain_chars: List[str] = []
    capturing = False
    buffer: List[str] = []

    for char in snippet:
        if char == SNIPPET_START:
            capturing = True
            buffer = []
            continue
        if char == SNIPPET_END:
            capturing = False
            term = "".join(buffer).strip()
            if term:
                highlights.append(term)
            plain_chars.append(term)
            continue
        if capturing:
            buffer.append(char)
        plain_chars.append(char)

    text_out = "".join(plain_chars)
    # De-duplicate while preserving order
    seen = set()
    unique = []
    for term in highlights:
        key = term.lower()
        if key not in seen:
            seen.add(key)
            unique.append(term)

    return text_out, unique
