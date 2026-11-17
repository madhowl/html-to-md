"""Опции конвертации."""

from __future__ import annotations

from dataclasses import dataclass

SUPPORTED_FORMATS = ("md", "pdf", "docx")


@dataclass(frozen=True, slots=True)
class ConvertOptions:
    formats: tuple[str, ...] = SUPPORTED_FORMATS
    page_break_before_h1: bool = False
    copy_assets: bool = True
    include_report: bool = True
    recursive: bool = True
    image_max_width_pt: float = 470.0

    def __post_init__(self) -> None:
        normalized = tuple(dict.fromkeys(self.formats))
        unknown = [item for item in normalized if item not in SUPPORTED_FORMATS]
        if unknown:
            raise ValueError(f"Неизвестные форматы: {', '.join(unknown)}")
        if not normalized:
            raise ValueError("Не выбран ни один формат")
        object.__setattr__(self, "formats", normalized)

    @classmethod
    def from_string(cls, value: str, **kwargs: object) -> ConvertOptions:
        formats = tuple(item.strip().lower() for item in value.split(",") if item.strip())
        return cls(formats=formats, **kwargs)  # type: ignore[arg-type]
