"""Chunking tests."""
import pytest

from app.indexing.chunker import chunk_document
from app.parsers.base import ParsedDocument, ParsedSection


def test_chunks_preserve_order_and_cover_text():
    text = " ".join(f"word{i}" for i in range(400))
    parsed = ParsedDocument(sections=[ParsedSection(text=text)])
    chunks = chunk_document(parsed, chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert chunks[0].content.startswith("word0")
    assert "word399" in chunks[-1].content


def test_chunks_do_not_cross_sections():
    parsed = ParsedDocument(
        sections=[
            ParsedSection(text="alpha " * 100, page_number=1),
            ParsedSection(text="beta " * 100, page_number=2),
        ]
    )
    chunks = chunk_document(parsed, chunk_size=120, chunk_overlap=10)

    alpha_chunks = [c for c in chunks if "alpha" in c.content]
    beta_chunks = [c for c in chunks if "beta" in c.content]

    assert alpha_chunks and beta_chunks
    for chunk in alpha_chunks:
        assert "beta" not in chunk.content
        assert chunk.page_number == 1
    for chunk in beta_chunks:
        assert "alpha" not in chunk.content
        assert chunk.page_number == 2


def test_overlap_is_applied():
    parsed = ParsedDocument(sections=[ParsedSection(text="abcdefghij" * 30)])
    chunks = chunk_document(parsed, chunk_size=100, chunk_overlap=30)
    # Consecutive chunks should share a suffix/prefix region
    assert len(chunks) >= 2
    shared = set(chunks[0].content[-30:]) & set(chunks[1].content[:30])
    assert shared


def test_invalid_parameters_rejected():
    parsed = ParsedDocument(sections=[ParsedSection(text="hello")])
    with pytest.raises(ValueError):
        chunk_document(parsed, chunk_size=0)
    with pytest.raises(ValueError):
        chunk_document(parsed, chunk_size=100, chunk_overlap=100)


def test_heading_preserved():
    parsed = ParsedDocument(
        sections=[ParsedSection(text="content " * 50, heading="Database setup")]
    )
    chunks = chunk_document(parsed, chunk_size=100, chunk_overlap=10)
    assert all(c.heading == "Database setup" for c in chunks)
