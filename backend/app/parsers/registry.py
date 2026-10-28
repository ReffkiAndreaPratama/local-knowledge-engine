"""Parser registry and dispatcher."""
import os
from typing import Callable

from app.core.config import settings
from app.parsers.base import ParsedDocument, ParseError
from app.parsers.office_parser import parse_docx, parse_xlsx
from app.parsers.pdf_parser import parse_pdf
from app.parsers.text_parser import (
    parse_csv,
    parse_html,
    parse_json,
    parse_markdown,
    parse_text,
)

# Extension -> parser
PARSERS: dict[str, Callable[[str], ParsedDocument]] = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".xlsx": parse_xlsx,
    ".md": parse_markdown,
    ".markdown": parse_markdown,
    ".csv": parse_csv,
    ".json": parse_json,
    ".html": parse_html,
    ".htm": parse_html,
    ".txt": parse_text,
}

# Source code extensions handled by the plain-text parser
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".css", ".scss", ".sh", ".bash", ".sql",
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".xml", ".kt", ".swift", ".cs",
    ".lua", ".pl", ".r", ".vue", ".svelte",
}

for ext in CODE_EXTENSIONS:
    if ext not in PARSERS:
        PARSERS[ext] = parse_text


def get_supported_extensions() -> set[str]:
    """Return all extensions the parser registry can handle."""
    return set(PARSERS.keys())


def is_supported(path: str) -> bool:
    """Check if the extension is supported and allowed by config."""
    ext = os.path.splitext(path)[1].lower()
    return ext in PARSERS and ext in settings.allowed_extensions_list


def parse_document(path: str) -> ParsedDocument:
    """Dispatch a file to the correct parser."""
    if not os.path.exists(path):
        raise ParseError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    parser = PARSERS.get(ext)
    if parser is None:
        raise ParseError(f"Unsupported file extension: {ext}")

    result = parser(path)
    if not result.text.strip():
        raise ParseError("Parser produced no text")

    return result
