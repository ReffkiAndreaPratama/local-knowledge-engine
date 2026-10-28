"""Parser tests."""
import json

import pytest

from app.parsers.base import ParseError
from app.parsers.registry import parse_document


def write(tmp_path, name, content, mode="w", encoding="utf-8"):
    path = tmp_path / name
    if mode == "wb":
        path.write_bytes(content)
    else:
        path.write_text(content, encoding=encoding)
    return str(path)


def test_parse_txt(tmp_path):
    path = write(tmp_path, "notes.txt", "Local search keeps data private.")
    parsed = parse_document(path)
    assert "private" in parsed.text
    assert parsed.char_count > 0


def test_parse_markdown_keeps_headings(tmp_path):
    content = "# Installation\n\nRun pip install.\n\n## Configuration\n\nEdit the env file."
    path = write(tmp_path, "readme.md", content)
    parsed = parse_document(path)
    headings = [s.heading for s in parsed.sections if s.heading]
    assert "Installation" in headings
    assert "Configuration" in headings


def test_parse_json_flattens_values(tmp_path):
    data = {"database": {"host": "localhost", "port": 5432}}
    path = write(tmp_path, "config.json", json.dumps(data))
    parsed = parse_document(path)
    assert "database.host: localhost" in parsed.text
    assert "database.port: 5432" in parsed.text


def test_parse_csv_includes_header_names(tmp_path):
    path = write(tmp_path, "data.csv", "name,role\nAna,engineer\nBudi,designer\n")
    parsed = parse_document(path)
    assert "name: Ana" in parsed.text
    assert "role: designer" in parsed.text


def test_parse_html_strips_scripts(tmp_path):
    html = "<html><body><h1>Title</h1><p>Visible text.</p><script>alert(1)</script></body></html>"
    path = write(tmp_path, "page.html", html)
    parsed = parse_document(path)
    assert "Visible text" in parsed.text
    assert "alert" not in parsed.text


def test_parse_source_code(tmp_path):
    path = write(tmp_path, "app.py", "def connect_database():\n    return 'ok'\n")
    parsed = parse_document(path)
    assert "connect_database" in parsed.text


def test_empty_file_is_rejected(tmp_path):
    path = write(tmp_path, "empty.txt", "   \n")
    with pytest.raises(ParseError):
        parse_document(path)


def test_unsupported_extension_is_rejected(tmp_path):
    path = write(tmp_path, "binary.bin", b"\x00\x01\x02", mode="wb")
    with pytest.raises(ParseError):
        parse_document(path)


def test_corrupt_pdf_is_reported_not_crashing(tmp_path):
    path = write(tmp_path, "broken.pdf", b"%PDF-1.4 definitely not a real pdf", mode="wb")
    with pytest.raises(ParseError):
        parse_document(path)


def test_docx_parsing(tmp_path):
    docx = pytest.importorskip("docx")
    document = docx.Document()
    document.add_heading("Project Plan", level=1)
    document.add_paragraph("Ship the indexing pipeline first.")
    path = str(tmp_path / "plan.docx")
    document.save(path)

    parsed = parse_document(path)
    assert "indexing pipeline" in parsed.text


def test_pdf_parsing(tmp_path):
    fitz = pytest.importorskip("pymupdf")
    path = str(tmp_path / "sample.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hybrid retrieval combines keyword and semantic search.")
    doc.save(path)
    doc.close()

    parsed = parse_document(path)
    assert "Hybrid retrieval" in parsed.text
    assert parsed.page_count == 1
    assert parsed.sections[0].page_number == 1
