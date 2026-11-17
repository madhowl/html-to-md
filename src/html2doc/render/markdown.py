"""Рендер Markdown (GFM)."""

from __future__ import annotations

import re
from urllib.parse import quote

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


def _escape(text: str) -> str:
    result = (
        text.replace("\\", "\\\\")
        .replace("`", "\\`")
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("|", "\\|")
    )
    return re.sub(r"^(\s*)([#>+-])", r"\1\\\2", result)


def _wrap_emphasis(text: str, prefix: str, suffix: str) -> str:
    stripped = text.strip()
    if not stripped:
        return text
    start = len(text) - len(text.lstrip())
    end = len(text.rstrip())
    return f"{text[:start]}{prefix}{stripped}{suffix}{text[end:]}"


def render_runs_md(runs: tuple[InlineRun, ...] | list[InlineRun]) -> str:
    parts: list[str] = []
    for run in runs:
        text = _escape(run.text).replace("\n", "  \n")
        if run.bold:
            text = _wrap_emphasis(text, "**", "**")
        if run.italic:
            text = _wrap_emphasis(text, "*", "*")
        if run.underline:
            text = _wrap_emphasis(text, "<u>", "</u>")
        parts.append(text)
    return "".join(parts)


def _render_table(table: Table) -> str:
    if not table.rows:
        return ""
    if table.html_fallback:
        return table.html_fallback.strip()

    columns = len(table.rows[0])
    if not columns:
        return ""

    def cells(row: tuple[tuple[InlineRun, ...], ...]) -> list[str]:
        rendered = [render_runs_md(cell).replace("\n", "<br>") for cell in row]
        rendered += [""] * (columns - len(rendered))
        return [item or " " for item in rendered[:columns]]

    header = table.rows[0] if table.header_rows else tuple(() for _ in range(columns))
    body = table.rows[table.header_rows :]
    lines = [
        "| " + " | ".join(cells(header)) + " |",
        "| " + " | ".join(["---"] * columns) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(cells(row)) + " |")
    return "\n".join(lines)


def _render_image(image: Image) -> str:
    if image.missing:
        return f"> Изображение не найдено: `{image.src}`"
    link = quote(str(image.asset_path).replace("\\", "/"), safe="/")
    alt = _escape(image.alt or image.caption or "")
    lines = [f"![{alt}]({link})"]
    if image.caption:
        lines.append(f"*{_escape(image.caption)}*")
    return "\n\n".join(lines)


def _render_blocks(blocks: list[Block], indent: str = "") -> list[str]:
    chunks: list[str] = []
    for block in blocks:
        chunk = _render_block(block)
        if not chunk:
            continue
        if indent:
            chunk = "\n".join(f"{indent}{line}" if line else line for line in chunk.split("\n"))
        chunks.append(chunk)
    return chunks


def _render_list(block: ListBlock) -> str:
    chunks: list[str] = []
    for index, item in enumerate(block.items, start=1):
        item_chunks = _render_blocks(item.blocks)
        if not item_chunks:
            continue
        if block.marker_style == "none":
            chunks.extend(item_chunks)
            continue
        prefix = "- " if block.marker_style == "bullet" else f"{index}. "
        first = item_chunks[0]
        continuation_indent = " " * len(prefix)
        if "\n" in first:
            first_lines = first.split("\n")
            first = prefix + first_lines[0]
            first += "\n" + "\n".join(
                continuation_indent + line if line else line for line in first_lines[1:]
            )
        else:
            first = prefix + first
        rest = [
            "\n".join(continuation_indent + line if line else line for line in part.split("\n"))
            for part in item_chunks[1:]
        ]
        chunks.append("\n\n".join([first, *rest]))
    return "\n\n".join(chunks)


def _render_block(block: Block) -> str:
    if isinstance(block, Heading):
        return f"{'#' * block.level} {render_runs_md(block.runs)}"
    if isinstance(block, Paragraph):
        return render_runs_md(block.runs)
    if isinstance(block, Table):
        return _render_table(block)
    if isinstance(block, Image):
        return _render_image(block)
    if isinstance(block, ListBlock):
        return _render_list(block)
    if isinstance(block, PageBreak):
        return "---"
    return ""


def render_markdown(document: Document) -> str:
    chunks = [chunk for block in document.blocks if (chunk := _render_block(block))]
    return "\n\n".join(chunks).rstrip() + "\n"
