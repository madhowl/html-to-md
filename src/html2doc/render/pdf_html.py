"""Промежуточный HTML для рендера PDF через WeasyPrint."""

from __future__ import annotations

import html
from pathlib import Path

from html2doc.models import (
    Block,
    Document,
    Heading,
    Image,
    InlineRun,
    ListBlock,
    PageBreak,
    Paragraph,
    Table,
)
from html2doc.options import ConvertOptions

_CSS = """
@page {
  size: A4;
  margin: 18mm 18mm 20mm 18mm;
}
body {
  font-family: "Times New Roman", "Liberation Serif", serif;
  font-size: 11pt;
  line-height: 1.35;
  color: #000;
}
h1, h2, h3 { margin: 10pt 0 6pt 0; }
h1 { font-size: 18pt; }
h2 { font-size: 14pt; }
h3 { font-size: 12pt; }
p { margin: 0 0 6pt 0; text-align: justify; }
p.caption, figcaption { font-style: italic; font-size: 9pt; text-align: center; }
.list-none-item { margin: 0 0 3pt 0; }
ul, ol { margin: 4pt 0 8pt 18pt; }
li { margin-bottom: 2pt; }
table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  margin: 8pt 0 10pt 0;
  font-size: 9pt;
  overflow-wrap: anywhere;
}
th, td { border: 1px solid #000; padding: 3pt 4pt; vertical-align: top; }
thead { display: table-header-group; }
tr, figure { break-inside: avoid; }
img { max-width: 100%; height: auto; }
figure { margin: 10pt 0; text-align: center; }
.missing { color: #a00; font-size: 9pt; }
.page-break { break-before: page; }
"""


def _escape(text: str) -> str:
    return html.escape(text, quote=False).replace("\n", "<br>")


def _wrap_emphasis(text: str, tag: str) -> str:
    stripped = text.strip()
    if not stripped:
        return text
    start = len(text) - len(text.lstrip())
    end = len(text.rstrip())
    return f"{text[:start]}<{tag}>{stripped}</{tag}>{text[end:]}"


def render_inline_html(runs: tuple[InlineRun, ...] | list[InlineRun]) -> str:
    parts: list[str] = []
    for run in runs:
        text = _escape(run.text)
        if run.bold:
            text = _wrap_emphasis(text, "strong")
        if run.italic:
            text = _wrap_emphasis(text, "em")
        if run.underline:
            text = _wrap_emphasis(text, "u")
        parts.append(text)
    return "".join(parts)


def _render_table(table: Table) -> str:
    if table.html_fallback:
        return f'<div class="table-wrap">{table.html_fallback}</div>'
    if not table.rows:
        return ""
    columns = len(table.rows[0])
    if not columns:
        return ""

    def row_html(row: tuple[tuple[InlineRun, ...], ...], *, header: bool) -> str:
        tag = "th" if header else "td"
        cells: list[str] = []
        for runs in row:
            content = render_inline_html(runs)
            cells.append(f"<{tag}>{content}</{tag}>")
        cells += [f"<{tag}></{tag}>"] * (columns - len(cells))
        return "<tr>" + "".join(cells[:columns]) + "</tr>"

    parts = ["<table>"]
    if table.header_rows:
        parts.append("<thead>" + row_html(table.rows[0], header=True) + "</thead>")
        body = table.rows[table.header_rows :]
    else:
        body = table.rows
    if body:
        parts.append("<tbody>" + "".join(row_html(row, header=False) for row in body) + "</tbody>")
    parts.append("</table>")
    return "".join(parts)


def _render_image(image: Image, output_dir: Path) -> str:
    if image.missing:
        return f'<p class="missing">{_escape(str(image.src))} — изображение не найдено</p>'
    path = output_dir / image.asset_path
    if not path.is_file():
        path = image.src
    if not path.is_file():
        return f'<p class="missing">{_escape(str(image.src))} — изображение не найдено</p>'
    uri = path.resolve().as_uri()
    size = ""
    if image.width_pt:
        size = f' style="width:{image.width_pt:g}pt"'
    caption = ""
    if image.caption:
        caption = f"<figcaption>{_escape(image.caption)}</figcaption>"
    return f'<figure><img src="{html.escape(uri, quote=True)}" alt="{html.escape(image.alt, quote=True)}"{size}>{caption}</figure>'


def _render_blocks(
    blocks: list[Block],
    output_dir: Path,
    options: ConvertOptions,
    state: dict[str, int],
) -> list[str]:
    parts: list[str] = []
    for block in blocks:
        if isinstance(block, Heading):
            css_class = ""
            if block.level == 1:
                css_class = ' class="first-h1"' if state["h1"] == 0 else ' class="page-break"'
                state["h1"] += 1
            if not options.page_break_before_h1:
                css_class = ""
            parts.append(f"<h{block.level}{css_class}>{render_inline_html(block.runs)}</h{block.level}>")
        elif isinstance(block, Paragraph):
            css_class = ' class="caption"' if block.style == "caption" else ""
            parts.append(f"<p{css_class}>{render_inline_html(block.runs)}</p>")
        elif isinstance(block, Table):
            parts.append(_render_table(block))
        elif isinstance(block, Image):
            parts.append(_render_image(block, output_dir))
        elif isinstance(block, ListBlock):
            if block.marker_style == "none":
                for item in block.items:
                    inner = "".join(_render_blocks(item.blocks, output_dir, options, state))
                    parts.append(f'<div class="list-none-item">{inner}</div>')
            else:
                tag = "ol" if block.marker_style == "number" else "ul"
                items = []
                for item in block.items:
                    inner = "".join(_render_blocks(item.blocks, output_dir, options, state))
                    items.append(f"<li>{inner}</li>")
                parts.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
        elif isinstance(block, PageBreak):
            parts.append('<div class="page-break"></div>')
    return parts


def build_pdf_html(
    document: Document,
    output_dir: Path,
    options: ConvertOptions,
) -> str:
    state = {"h1": 0}
    body = "".join(_render_blocks(document.blocks, output_dir, options, state))
    page_break_css = "h1.page-break, .page-break { break-before: page; }" if options.page_break_before_h1 else ""
    return (
        "<!doctype html><html lang=\"ru\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(document.title, quote=True)}</title>"
        f"<style>{_CSS}\n{page_break_css}</style></head><body>{body}</body></html>"
    )
