"""Base parser definitions."""
from dataclasses import dataclass, field
from typing import List, Optional


class ParseError(Exception):
    """Raised when a document cannot be parsed."""


@dataclass
class ParsedSection:
    """A section of extracted text with optional source location."""
    text: str
    page_number: Optional[int] = None
    heading: Optional[str] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None


@dataclass
class ParsedDocument:
    """Result of parsing a document."""
    sections: List[ParsedSection] = field(default_factory=list)
    page_count: Optional[int] = None

    @property
    def text(self) -> str:
        return "\n\n".join(s.text for s in self.sections if s.text).strip()

    @property
    def char_count(self) -> int:
        return len(self.text)
