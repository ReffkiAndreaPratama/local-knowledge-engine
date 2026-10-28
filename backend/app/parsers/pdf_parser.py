"""PDF parser using PyMuPDF."""
from app.parsers.base import ParsedDocument, ParsedSection, ParseError


def parse_pdf(path: str) -> ParsedDocument:
    """Extract text from a PDF, page by page."""
    try:
        import pymupdf
    except ImportError as exc:
        raise ParseError("PyMuPDF is not installed") from exc

    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise ParseError(f"Cannot open PDF: {exc}") from exc

    sections = []
    try:
        if doc.needs_pass:
            raise ParseError("PDF is password protected")

        page_count = doc.page_count
        for page_index in range(page_count):
            page = doc.load_page(page_index)
            text = page.get_text("text").strip()
            if text:
                sections.append(
                    ParsedSection(text=text, page_number=page_index + 1)
                )
    finally:
        doc.close()

    if not sections:
        raise ParseError(
            "No extractable text found. This PDF may be scanned images; OCR is required."
        )

    return ParsedDocument(sections=sections, page_count=page_count)
