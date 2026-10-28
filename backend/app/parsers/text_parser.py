"""Text, Markdown, and source-code parsers."""
import json
import re

from app.parsers.base import ParsedDocument, ParsedSection, ParseError


def parse_text(path: str) -> ParsedDocument:
    """Parse a plain text file (also used for source code)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as exc:
        raise ParseError(f"Cannot read file: {exc}") from exc

    if not content.strip():
        raise ParseError("File is empty or contains no readable text")

    return ParsedDocument(sections=[ParsedSection(text=content, start_char=0, end_char=len(content))])


def parse_markdown(path: str) -> ParsedDocument:
    """Parse Markdown, keeping headings as source metadata."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as exc:
        raise ParseError(f"Cannot read file: {exc}") from exc

    if not content.strip():
        raise ParseError("File is empty or contains no readable text")

    sections = []
    current_heading = None
    buffer = []
    heading_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

    def flush():
        text = "\n".join(buffer).strip()
        if text:
            sections.append(ParsedSection(text=text, heading=current_heading))
        buffer.clear()

    for line in content.splitlines():
        match = heading_pattern.match(line)
        if match:
            flush()
            current_heading = match.group(2).strip()
            buffer.append(line)
        else:
            buffer.append(line)
    flush()

    if not sections:
        raise ParseError("No readable sections found in Markdown")

    return ParsedDocument(sections=sections)


def parse_csv(path: str) -> ParsedDocument:
    """Parse CSV into row-oriented text."""
    import csv

    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            sample = f.read(8192)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.reader(f, dialect)
            rows = list(reader)
    except OSError as exc:
        raise ParseError(f"Cannot read file: {exc}") from exc

    if not rows:
        raise ParseError("CSV file has no rows")

    header = rows[0]
    lines = []
    for row in rows[1:]:
        pairs = []
        for idx, value in enumerate(row):
            column = header[idx] if idx < len(header) else f"column_{idx}"
            pairs.append(f"{column}: {value}")
        lines.append(" | ".join(pairs))

    text = "\n".join(lines) if lines else " | ".join(header)
    if not text.strip():
        raise ParseError("CSV contains no data rows")

    return ParsedDocument(sections=[ParsedSection(text=text)])


def parse_json(path: str) -> ParsedDocument:
    """Parse JSON into flattened readable text."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except OSError as exc:
        raise ParseError(f"Cannot read file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON: {exc}") from exc

    lines = []

    def walk(node, prefix=""):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{prefix}.{key}" if prefix else str(key))
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                walk(value, f"{prefix}[{idx}]")
        else:
            lines.append(f"{prefix}: {node}")

    walk(data)
    text = "\n".join(lines)
    if not text.strip():
        raise ParseError("JSON contains no scalar values")

    return ParsedDocument(sections=[ParsedSection(text=text)])


def parse_html(path: str) -> ParsedDocument:
    """Parse HTML to plain text."""
    from bs4 import BeautifulSoup

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw = f.read()
    except OSError as exc:
        raise ParseError(f"Cannot read file: {exc}") from exc

    soup = BeautifulSoup(raw, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    sections = []
    for heading in soup.find_all(re.compile("^h[1-6]$")):
        heading_text = heading.get_text(strip=True)
        if not heading_text:
            continue
        parts = []
        for sibling in heading.next_siblings:
            if getattr(sibling, "name", None) and re.match(r"^h[1-6]$", sibling.name):
                break
            if getattr(sibling, "get_text", None):
                parts.append(sibling.get_text(" ", strip=True))
            elif isinstance(sibling, str):
                parts.append(sibling.strip())
        body = " ".join(p for p in parts if p).strip()
        if body:
            sections.append(ParsedSection(text=body, heading=heading_text))

    if not sections:
        text = soup.get_text("\n", strip=True)
        if not text:
            raise ParseError("HTML contains no readable text")
        sections = [ParsedSection(text=text)]

    return ParsedDocument(sections=sections)
