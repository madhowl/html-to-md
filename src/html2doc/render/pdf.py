"""Рендер PDF через WeasyPrint."""

from __future__ import annotations

from pathlib import Path

from weasyprint import HTML

from html2doc.errors import ConversionError
from html2doc.models import Document
from html2doc.options import ConvertOptions
from html2doc.render.pdf_html import build_pdf_html


def render_pdf(document: Document, output_dir: Path, options: ConvertOptions) -> None:
    target = output_dir / f"{document.title}.pdf"
    markup = build_pdf_html(document, output_dir, options)
    try:
        HTML(string=markup, base_url=str(output_dir)).write_pdf(str(target))
    except Exception as exc:
        raise ConversionError(f"Не удалось создать PDF: {exc}") from exc
