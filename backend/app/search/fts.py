"""SQLite FTS5 virtual table management and safe query building.

User input is never interpolated into SQL. Every term is turned into a quoted
FTS5 string, which means FTS5 syntax characters cannot break out of the
expression.
"""
import re
from typing import List, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

FTS_TABLE = "chunk_fts"

CREATE_FTS_SQL = f"""
CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5(
    content,
    chunk_id UNINDEXED,
    document_id UNINDEXED,
    filename,
    extension UNINDEXED,
    heading,
    tokenize = 'unicode61 remove_diacritics 2'
)
"""

_OPERATORS = {"AND", "OR", "NOT"}
_TOKEN_RE = re.compile(r'"([^"]*)"|(\S+)')
_UNSAFE_CHARS = re.compile(r'[*^:()"\u0000-\u001f]')

# Very common words carry little signal in a local document index. They are
# only dropped from the OR fallback query, never from a precise AND query.
STOPWORDS = {
    # English
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "did", "do", "does", "for", "from", "had", "has", "have", "how", "i",
    "if", "in", "into", "is", "it", "its", "of", "on", "or", "should", "so",
    "that", "the", "their", "then", "there", "these", "they", "this", "to",
    "was", "were", "what", "when", "where", "which", "who", "why", "will",
    "with", "would", "you", "your",
    # Indonesian
    "ada", "adalah", "apa", "apakah", "bagaimana", "bagi", "bahwa", "dan",
    "dari", "dengan", "di", "dimana", "ini", "itu", "jika", "juga", "ke",
    "kapan", "karena", "mana", "mengapa", "oleh", "pada", "saat", "saya",
    "sebuah", "serta", "siapa", "tidak", "untuk", "yang",
}


def ensure_fts_table(db: Session) -> None:
    """Create the FTS5 table if it does not exist."""
    db.execute(text(CREATE_FTS_SQL))
    db.commit()


def index_chunk(
    db: Session,
    chunk_id: str,
    document_id: str,
    content: str,
    filename: str,
    extension: str,
    heading: str | None,
) -> None:
    """Add or replace a single chunk in the FTS index."""
    db.execute(
        text(f"DELETE FROM {FTS_TABLE} WHERE chunk_id = :chunk_id"),
        {"chunk_id": chunk_id},
    )
    db.execute(
        text(
            f"INSERT INTO {FTS_TABLE} "
            "(content, chunk_id, document_id, filename, extension, heading) "
            "VALUES (:content, :chunk_id, :document_id, :filename, :extension, :heading)"
        ),
        {
            "content": content,
            "chunk_id": chunk_id,
            "document_id": document_id,
            "filename": filename,
            "extension": extension,
            "heading": heading or "",
        },
    )


def delete_document_chunks(db: Session, document_id: str) -> None:
    """Remove all FTS entries belonging to a document."""
    db.execute(
        text(f"DELETE FROM {FTS_TABLE} WHERE document_id = :document_id"),
        {"document_id": document_id},
    )


def clear_fts(db: Session) -> None:
    """Remove every entry from the FTS table."""
    db.execute(text(f"DELETE FROM {FTS_TABLE}"))
    db.commit()


def build_fts_query(raw_query: str, operator: str = "AND") -> str | None:
    """Convert free-form user input into a safe FTS5 MATCH expression.

    Returns None when there is nothing searchable.
    """
    terms, explicit_operators = _parse(raw_query)
    if not terms:
        return None

    if explicit_operators:
        parts: List[str] = []
        for index, term in enumerate(terms):
            if index > 0:
                parts.append(explicit_operators.get(index, "AND"))
            parts.append(term)
        return " ".join(parts)

    joiner = operator if operator in _OPERATORS else "AND"
    return f" {joiner} ".join(terms)


def build_fts_fallback_query(raw_query: str) -> str | None:
    """Build a broader OR query, dropping stopwords when enough terms remain."""
    terms, _ = _parse(raw_query)
    if not terms:
        return None

    plain = [term.strip('"*') for term in terms]
    informative = [term for term in plain if term.lower() not in STOPWORDS]
    if len(informative) >= 2 and len(informative) < len(plain):
        return " OR ".join(f'"{term}"*' for term in informative)
    return " OR ".join(terms)


def _parse(raw_query: str | None) -> Tuple[List[str], dict]:
    """Split input into safe quoted terms plus any user-supplied operators."""
    if raw_query is None:
        return [], {}
    raw_query = raw_query.strip()
    if not raw_query:
        return [], {}

    terms: List[str] = []
    explicit: dict[int, str] = {}

    for match in _TOKEN_RE.finditer(raw_query):
        phrase, word = match.group(1), match.group(2)

        if phrase is not None:
            cleaned = _clean(phrase)
            if cleaned:
                terms.append(f'"{cleaned}"')
            continue

        if word is None:
            continue

        upper = word.upper()
        if upper in {"AND", "OR"} and terms:
            explicit[len(terms)] = upper
            continue
        if upper == "NOT":
            # NOT is ignored: excluding terms silently hides documents and is
            # easy to get wrong with an incomplete query.
            continue

        cleaned = _clean(word)
        if not cleaned:
            continue
        if len(cleaned) >= 3:
            terms.append(f'"{cleaned}"*')
        else:
            terms.append(f'"{cleaned}"')

    # Drop dangling operators (e.g. "foo OR")
    while explicit and len(terms) in explicit:
        explicit.pop(len(terms), None)

    return terms, explicit


def _clean(value: str) -> str:
    value = _UNSAFE_CHARS.sub(" ", value)
    return " ".join(value.split())
