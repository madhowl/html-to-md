"""Сбор и сериализация предупреждений конвертации."""

from __future__ import annotations

import json
from typing import Literal

from html2doc.models import ConversionWarning


class WarningCollector:
    def __init__(self) -> None:
        self.items: list[ConversionWarning] = []

    def add(
        self,
        code: str,
        message: str,
        location: str = "",
        severity: Literal["info", "warning", "error"] = "warning",
    ) -> None:
        self.items.append(ConversionWarning(code, message, location, severity))

    def extend(self, warnings: list[ConversionWarning]) -> None:
        self.items.extend(warnings)


def write_report(
    path,
    *,
    source: str,
    formats: tuple[str, ...],
    warnings: list[ConversionWarning],
    stats: dict[str, int],
) -> None:
    payload = {
        "source": source,
        "formats": list(formats),
        "warnings": [item.as_dict() for item in warnings],
        "stats": stats,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
