"""Text chunking with source-location preservation."""
from dataclasses import dataclass
from typing import List

from app.parsers.base import ParsedDocument


@dataclass
class Chunk:
    """A chunk of text ready for indexing."""
    content: str
    chunk_index: int
    page_number: int | None = None
    heading: str | None = None
    start_char: int | None = None
    end_char: int | None = None


def chunk_document(
    parsed: ParsedDocument,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
) -> List[Chunk]:
    """Split a parsed document into overlapping chunks.

    Chunks never span two different sections (and therefore never two
    different documents). The chunker prefers paragraph and sentence
    boundaries so that chunks stay readable.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: List[Chunk] = []
    index = 0

    for section in parsed.sections:
        text = section.text.strip()
        if not text:
            continue

        # Keep track of the absolute offset within the section
        pos = 0
        length = len(text)

        while pos < length:
            end = min(pos + chunk_size, length)

            # Try to end on a natural boundary when possible
            if end < length:
                window = text[pos:end]
                boundary = _find_boundary(window, min_boundary=int(chunk_size * 0.5))
                if boundary > 0:
                    end = pos + boundary

            content = text[pos:end].strip()
            if content:
                chunks.append(
                    Chunk(
                        content=content,
                        chunk_index=index,
                        page_number=section.page_number,
                        heading=section.heading,
                        start_char=section.start_char + pos if section.start_char is not None else pos,
                        end_char=section.start_char + end if section.start_char is not None else end,
                )
                )
                index += 1

            if end >= length:
                break

            # Next window starts `overlap` characters before the end
            next_pos = max(end - chunk_overlap, pos + 1)
            pos = next_pos

    return chunks


def _find_boundary(text: str, min_boundary: int) -> int:
    """Find a good split point inside `text`, or 0 if none is suitable."""
    for sep in ("\n\n", "\n", ". ", "! ", "? ", "; ", ", "):
        idx = text.rfind(sep)
        if idx >= min_boundary:
            return idx + len(sep)
    return 0
