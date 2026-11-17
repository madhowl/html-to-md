"""Утилиты для поиска ресурсов в исходной и frozen-сборке."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> Path:
    if is_frozen():
        return Path(str(getattr(sys, "_MEIPASS", Path(__file__).parent)))
    return Path(__file__).parent


def resource_path(relative: str) -> Path:
    return bundle_dir() / Path(relative)
