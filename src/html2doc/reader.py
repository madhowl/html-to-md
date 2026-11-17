"""Чтение и первичная очистка HTML."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup, Comment

from html2doc.errors import ConversionError
from html2doc.report import WarningCollector


def decode_html(raw: bytes) -> tuple[str, str | None]:
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig"), None
    for encoding in ("utf-8", "cp1251"):
        try:
            return raw.decode(encoding), encoding if encoding == "cp1251" else None
        except UnicodeDecodeError:
            continue
    raise ConversionError("Не удалось определить кодировку HTML-файла")


def read_html(path: Path, collector: WarningCollector) -> BeautifulSoup:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConversionError(f"Не удалось прочитать {path}: {exc}") from exc

    text, encoding = decode_html(raw)
    if encoding:
        collector.add("encoding_fallback", f"Использована кодировка {encoding}", "file")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    try:
        soup = BeautifulSoup(text, "lxml")
    except Exception:
        soup = BeautifulSoup(text, "html.parser")
        collector.add("parser_fallback", "Использован резервный парсер html.parser", "file")

    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()

    if soup.body is None:
        collector.add("missing_body", "Тег <body> не найден", "file", "warning")

    return soup
