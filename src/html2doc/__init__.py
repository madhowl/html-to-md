"""html2doc — конвертер HTML/HTM в Markdown, PDF и DOCX."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("html2doc")
except PackageNotFoundError:
    __version__ = "0.1.0"
