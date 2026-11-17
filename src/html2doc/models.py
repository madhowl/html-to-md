"""Промежуточное представление документа."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias


@dataclass(frozen=True, slots=True)
class InlineRun:
    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass(frozen=True, slots=True)
class Paragraph:
    runs: tuple[InlineRun, ...] = ()
    style: Literal["normal", "caption"] = "normal"


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    runs: tuple[InlineRun, ...]


@dataclass(slots=True)
class ListItem:
    blocks: list[Block] = field(default_factory=list)
    marker: str | None = None


@dataclass(frozen=True, slots=True)
class ListBlock:
    items: tuple[ListItem, ...] = ()
    marker_style: Literal["none", "bullet", "number"] = "none"


@dataclass(frozen=True, slots=True)
class Table:
    rows: tuple[tuple[tuple[InlineRun, ...], ...], ...] = ()
    header_rows: int = 0
    html_fallback: str | None = None


@dataclass(frozen=True, slots=True)
class Image:
    src: Path
    asset_path: Path
    width_pt: float | None = None
    height_pt: float | None = None
    alt: str = ""
    caption: str | None = None
    missing: bool = False


@dataclass(frozen=True, slots=True)
class PageBreak:
    pass


@dataclass(frozen=True, slots=True)
class ConversionWarning:
    code: str
    message: str
    location: str = ""
    severity: Literal["info", "warning", "error"] = "warning"

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "location": self.location,
        }


@dataclass(slots=True)
class DocumentStats:
    headings: int = 0
    paragraphs: int = 0
    lists: int = 0
    tables: int = 0
    images: int = 0
    copied_assets: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "headings": self.headings,
            "paragraphs": self.paragraphs,
            "lists": self.lists,
            "tables": self.tables,
            "images": self.images,
            "copied_assets": self.copied_assets,
        }


Block: TypeAlias = Heading | Paragraph | ListBlock | Table | Image | PageBreak


@dataclass(slots=True)
class Document:
    title: str
    source: Path
    blocks: list[Block] = field(default_factory=list)
    warnings: list[ConversionWarning] = field(default_factory=list)
    stats: DocumentStats = field(default_factory=DocumentStats)
