"""Преобразование BeautifulSoup DOM в промежуточную модель документа."""

from __future__ import annotations

import html
import re
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from html2doc.assets import destination_for_image, natural_size_pt, resolve_image, style_lengths
from html2doc.models import (
    Block,
    Document,
    DocumentStats,
    Heading,
    Image,
    InlineRun,
    ListBlock,
    ListItem,
    PageBreak,
    Paragraph,
    Table,
)
from html2doc.report import WarningCollector

BR = "\x00"
CAPTION_RE = re.compile(r"^\s*(?:рисунок|figure)\s+(\d+)\b", re.IGNORECASE)
MANUAL_MARKER_RE = re.compile(
    r"^\s*(?:[•▪‣∙·]\s+|[-–—]\s+|\d+(?:\.\d+)*[.)]?\s+|[a-zA-Zа-яА-ЯёЁ][.)]\s+)"
)
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_ALLOWED_TABLE_TAGS = {
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "p", "span", "br", "b", "strong", "i", "em", "u", "div"
}
_SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link", "title"}


@dataclass(frozen=True, slots=True)
class _Flags:
    bold: bool = False
    italic: bool = False
    underline: bool = False

    def with_tag(self, tag: Tag) -> _Flags:
        bold = self.bold
        italic = self.italic
        underline = self.underline
        if tag.name in {"b", "strong"}:
            bold = True
        if tag.name in {"i", "em", "cite"}:
            italic = True
        if tag.name == "u":
            underline = True
        declarations = _style_declarations(tag)
        weight = declarations.get("font-weight", "").lower()
        if weight in {"bold", "bolder", "700", "800", "900"}:
            bold = True
        if declarations.get("font-style", "").lower() in {"italic", "oblique"}:
            italic = True
        decoration = declarations.get("text-decoration", "").lower()
        decoration_line = declarations.get("text-decoration-line", "").lower()
        if "underline" in decoration or "underline" in decoration_line:
            underline = True
        return _Flags(bold, italic, underline)


@dataclass(slots=True)
class _Context:
    source: Path
    collector: WarningCollector


def _style_declarations(tag: Tag) -> dict[str, str]:
    result: dict[str, str] = {}
    style = tag.get("style")
    if not isinstance(style, str):
        return result
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        result[key.strip().lower()] = value.strip()
    return result


def _append_run(parts: list[InlineRun], text: str, flags: _Flags) -> None:
    if not text:
        return
    if parts and (parts[-1].bold, parts[-1].italic, parts[-1].underline) == (
        flags.bold,
        flags.italic,
        flags.underline,
    ):
        parts[-1] = replace(parts[-1], text=parts[-1].text + text)
    else:
        parts.append(InlineRun(text, flags.bold, flags.italic, flags.underline))


def _text_to_runs(text: str, flags: _Flags) -> list[InlineRun]:
    parts: list[InlineRun] = []
    for index, segment in enumerate(text.split(BR)):
        if index:
            _append_run(parts, "\n", flags)
        cleaned = segment.replace("\xa0", " ").replace("\u200b", "")
        cleaned = re.sub(r"\s+", " ", cleaned)
        _append_run(parts, cleaned, flags)
    return parts


def _finalize_runs(parts: list[InlineRun]) -> tuple[InlineRun, ...]:
    normalized: list[InlineRun] = []
    for part in parts:
        text = re.sub(r" *\n *", "\n", part.text)
        normalized.append(replace(part, text=text))
    while normalized and not normalized[0].text.strip():
        normalized.pop(0)
    while normalized and not normalized[-1].text.strip():
        normalized.pop()
    if normalized:
        normalized[0] = replace(normalized[0], text=normalized[0].text.lstrip())
        normalized[-1] = replace(normalized[-1], text=normalized[-1].text.rstrip())

    result: list[InlineRun] = []
    for part in normalized:
        if not part.text:
            continue
        if result and (result[-1].bold, result[-1].italic, result[-1].underline) == (
            part.bold,
            part.italic,
            part.underline,
        ):
            result[-1] = replace(result[-1], text=result[-1].text + part.text)
        else:
            result.append(part)
    return tuple(result)


def _is_empty_anchor(tag: Tag) -> bool:
    return tag.name == "a" and not tag.get_text(strip=True) and bool(tag.get("name"))


def inline_runs(node: Tag | NavigableString, flags: _Flags | None = None) -> tuple[InlineRun, ...]:
    parts: list[InlineRun] = []

    def visit(current: Any, current_flags: _Flags) -> None:
        if isinstance(current, NavigableString):
            parts.extend(_text_to_runs(str(current), current_flags))
            return
        if not isinstance(current, Tag):
            return
        name = current.name.lower()
        if name in _SKIP_TAGS or name == "img":
            return
        if name == "br":
            if current.has_attr("clear"):
                return
            parts.extend(_text_to_runs(BR, current_flags))
            return
        if _is_empty_anchor(current):
            return
        next_flags = current_flags.with_tag(current)
        for child in current.children:
            visit(child, next_flags)

    visit(node, flags or _Flags())
    return _finalize_runs(parts)


def runs_text(runs: tuple[InlineRun, ...] | list[InlineRun]) -> str:
    return "".join(run.text for run in runs)


def _strip_bold(runs: tuple[InlineRun, ...]) -> tuple[InlineRun, ...]:
    return tuple(replace(run, bold=False) for run in runs)


def split_heading_runs(runs: tuple[InlineRun, ...]) -> list[tuple[InlineRun, ...]]:
    chars: list[tuple[str, InlineRun]] = []
    for run in runs:
        for char in run.text:
            chars.append((char, run))

    segments: list[list[InlineRun]] = [[]]
    index = 0
    while index < len(chars):
        char, run = chars[index]
        if char == "\n":
            end = index
            while end < len(chars) and chars[end][0] == "\n":
                end += 1
            if end - index >= 2:
                if segments[-1]:
                    segments.append([])
            else:
                _append_run(segments[-1], " ", _Flags(run.bold, run.italic, run.underline))
            index = end
            continue
        text = ""
        while index < len(chars) and chars[index][0] != "\n" and chars[index][1] is run:
            text += chars[index][0]
            index += 1
        _append_run(segments[-1], text, _Flags(run.bold, run.italic, run.underline))

    if len(segments) > 1 and not segments[-1]:
        segments.pop()
    return [segment for segment in (_finalize_runs(item) for item in segments) if segment]


def detect_marker(runs: tuple[InlineRun, ...]) -> str | None:
    match = MANUAL_MARKER_RE.match(runs_text(runs))
    return match.group(0).strip() if match else None


def clean_soup(soup: Any) -> None:
    for tag in list(soup.find_all(_SKIP_TAGS)):
        tag.decompose()
    for anchor in list(soup.find_all("a")):
        if _is_empty_anchor(anchor):
            anchor.decompose()
    for br in list(soup.find_all("br")):
        if br.has_attr("clear"):
            br.decompose()


def _location(tag: Tag) -> str:
    line = getattr(tag, "sourceline", None)
    return f"{tag.name}:{line}" if line is not None else tag.name


def convert_node(node: Any, ctx: _Context) -> list[Block]:
    if isinstance(node, NavigableString):
        runs = inline_runs(node)
        return [Paragraph(runs)] if runs else []
    if not isinstance(node, Tag):
        return []

    name = node.name.lower()
    if name in _SKIP_TAGS or name == "br":
        return []
    if name in _HEADING_TAGS:
        level = min(int(name[1]), 3)
        segments = split_heading_runs(inline_runs(node))
        return [Heading(level, _strip_bold(segment)) for segment in segments]
    if name == "p":
        return _convert_paragraph(node, ctx)
    if name in {"ul", "ol"}:
        return _convert_list(node, ctx)
    if name == "table":
        table = _convert_table(node, ctx)
        return [table] if table is not None else []
    if name == "img":
        image = _convert_image(node, ctx)
        return [image] if image is not None else []
    if name == "hr":
        return [PageBreak()]

    children = _convert_children(node, ctx)
    if children:
        return children
    runs = inline_runs(node)
    return [Paragraph(runs)] if runs else []


def _convert_children(node: Tag, ctx: _Context) -> list[Block]:
    blocks: list[Block] = []
    for child in node.children:
        blocks.extend(convert_node(child, ctx))
    return blocks


def _convert_paragraph(node: Tag, ctx: _Context) -> list[Block]:
    images = [img for img in node.find_all("img") if _belongs_to(img, node)]
    if not images:
        runs = inline_runs(node)
        if not runs:
            return []
        text = runs_text(runs).strip()
        style = "caption" if CAPTION_RE.match(text) else "normal"
        return [Paragraph(runs, style)]  # type: ignore[arg-type]

    clone = BeautifulSoup(str(node), "lxml").find("p")
    blocks: list[Block] = []
    if isinstance(clone, Tag):
        for img in clone.find_all("img"):
            img.decompose()
        runs = inline_runs(clone)
        if runs:
            blocks.append(Paragraph(runs))
    for img in images:
        converted = _convert_image(img, ctx)
        if converted is not None:
            blocks.append(converted)
    return blocks


def _belongs_to(tag: Tag, root: Tag) -> bool:
    parent = tag.parent
    while parent is not None and isinstance(parent, Tag):
        if parent is root:
            return True
        if parent.name == "table":
            return False
        parent = parent.parent
    return False


def _convert_list(node: Tag, ctx: _Context) -> list[Block]:
    style = node.get("style", "") or ""
    normalized_style = re.sub(r"\s+", "", str(style)).lower()
    if node.name == "ol":
        marker_style: Any = "number"
    elif "list-style:none" in normalized_style:
        marker_style = "none"
    else:
        marker_style = "bullet"

    flattened: list[Block] = []
    items: list[ListItem] = []
    marker_count = 0
    for li in node.find_all("li", recursive=False):
        child_blocks = _convert_children(li, ctx)
        if any(isinstance(block, Heading) for block in child_blocks):
            flattened.extend(child_blocks)
            continue
        marker = detect_marker(inline_runs(li))
        if marker:
            marker_count += 1
        items.append(ListItem(blocks=child_blocks, marker=marker))

    if marker_count:
        ctx.collector.add(
            "manual_marker",
            f"Ручные маркеры оставлены в тексте: {marker_count}",
            _location(node),
            "info",
        )
    if not items:
        return flattened
    return flattened + [ListBlock(items=tuple(items), marker_style=marker_style)]


def _sanitize_table(table: Tag) -> str:
    def render(node: Any) -> str:
        if isinstance(node, NavigableString):
            return html.escape(str(node))
        if not isinstance(node, Tag):
            return ""
        name = node.name.lower()
        if name not in _ALLOWED_TABLE_TAGS:
            return "".join(render(child) for child in node.children)
        attributes = ""
        for key in ("colspan", "rowspan"):
            value = node.get(key)
            if value is not None:
                attributes += f' {key}="{html.escape(str(value), quote=True)}"'
        content = "".join(render(child) for child in node.children)
        if name == "br":
            return "<br>"
        return f"<{name}{attributes}>{content}</{name}>"

    return render(table)


def _convert_table(node: Tag, ctx: _Context) -> Table | None:
    rows_tags = [tr for tr in node.find_all("tr") if _belongs_to(tr, node)]
    if not rows_tags:
        return None

    grid: list[list[tuple[InlineRun, ...]]] = []
    occupied: set[tuple[int, int]] = set()
    has_spans = False
    widths: list[int] = []

    for row_index, tr in enumerate(rows_tags):
        while len(grid) <= row_index:
            grid.append([])
        cells = [cell for cell in tr.find_all(["td", "th"], recursive=False)]
        if not cells:
            cells = [cell for cell in tr.find_all(["td", "th"]) if _belongs_to(cell, tr)]
        column = 0
        for cell in cells:
            while (row_index, column) in occupied:
                column += 1
            colspan = _positive_int(cell.get("colspan"), 1)
            rowspan = _positive_int(cell.get("rowspan"), 1)
            if colspan > 1 or rowspan > 1:
                has_spans = True
            runs = inline_runs(cell)
            for offset_row in range(rowspan):
                target_row = row_index + offset_row
                while len(grid) <= target_row:
                    grid.append([])
                for offset_col in range(colspan):
                    target_col = column + offset_col
                    while len(grid[target_row]) <= target_col:
                        grid[target_row].append(())
                    if offset_row == 0 and offset_col == 0:
                        grid[target_row][target_col] = runs
                    else:
                        occupied.add((target_row, target_col))
                        if not grid[target_row][target_col]:
                            grid[target_row][target_col] = ()
            column += colspan
        widths.append(column)

    if not grid:
        return None
    columns = max(len(row) for row in grid)
    for row in grid:
        while len(row) < columns:
            row.append(())

    first_row_tags = rows_tags[0].find_all(["td", "th"], recursive=False)
    has_th = any(cell.name == "th" for cell in first_row_tags)
    first_row_is_bold = bool(grid[0]) and all(
        cell and all(run.bold for run in cell) for cell in grid[0]
    )
    header_rows = 1 if has_th or first_row_is_bold else 0

    ragged = len(set(widths)) > 1
    fallback = _sanitize_table(node) if has_spans or ragged else None
    location = _location(node)
    if has_spans:
        ctx.collector.add("colspan_table", "Таблица содержит объединённые ячейки", location)
    if ragged:
        ctx.collector.add("ragged_table", "Строки таблицы имеют разную ширину", location)

    suspicious = 0
    for row in grid:
        for cell in row:
            text = runs_text(cell).strip()
            if len(text) == 1 and re.fullmatch(r"[A-Za-zА-Яа-яЁё]", text):
                suspicious += 1
    if suspicious:
        ctx.collector.add(
            "suspicious_cell",
            f"Обнаружено ячеек с одним символом: {suspicious}",
            location,
            "info",
        )

    return Table(
        rows=tuple(tuple(row) for row in grid),
        header_rows=header_rows,
        html_fallback=fallback,
    )


def _convert_image(node: Tag, ctx: _Context) -> Image | None:
    raw_src = node.get("src")
    src = str(raw_src) if raw_src is not None else ""
    resolved = resolve_image(ctx.source, src)
    width, height = style_lengths(str(node.get("style", "")))
    natural_width, natural_height = natural_size_pt(resolved) if resolved else (None, None)

    if width is None and height is None:
        width, height = natural_width, natural_height
    elif width is None and height is not None and natural_width and natural_height:
        width = round(height * natural_width / natural_height, 2)
    elif height is None and width is not None and natural_width and natural_height:
        height = round(width * natural_height / natural_width, 2)

    if resolved is None:
        ctx.collector.add(
            "missing_image",
            f"Изображение не найдено: {src or '(пустой src)'}",
            _location(node),
        )
        fallback = Path(src).name or "missing-image"
        return Image(
            src=Path(src) if src else ctx.source,
            asset_path=Path("assets") / fallback,
            width_pt=width,
            height_pt=height,
            alt=str(node.get("alt", "")) or "",
            missing=True,
        )

    return Image(
        src=resolved,
        asset_path=destination_for_image(ctx.source, resolved),
        width_pt=width,
        height_pt=height,
        alt=str(node.get("alt", "")) or "",
    )


def _link_images_and_captions(blocks: list[Block], ctx: _Context) -> None:
    section_starts = [
        index
        for index, block in enumerate(blocks)
        if isinstance(block, Heading) and block.level == 1
    ]
    if not section_starts:
        section_starts = [0]
    boundaries = section_starts + [len(blocks)]
    to_remove: set[int] = set()
    used_images: set[int] = set()

    for section_index in range(len(boundaries) - 1):
        start = boundaries[section_index]
        end = boundaries[section_index + 1]
        image_indices = [
            index for index in range(start, end) if isinstance(blocks[index], Image)
        ]
        caption_candidates: list[tuple[int, int]] = []
        for index in range(start, end):
            block = blocks[index]
            if not isinstance(block, Paragraph):
                continue
            text = runs_text(block.runs).strip()
            match = CAPTION_RE.match(text)
            if match:
                caption_candidates.append((index, int(match.group(1))))

        for caption_index, number in caption_candidates:
            block = blocks[caption_index]
            assert isinstance(block, Paragraph)
            text = runs_text(block.runs).strip()
            chosen: int | None = None
            by_number = number - 1
            if 0 <= by_number < len(image_indices):
                candidate = image_indices[by_number]
                if candidate not in used_images:
                    chosen = candidate
            if chosen is None:
                free = [index for index in image_indices if index not in used_images]
                if free:
                    chosen = min(free, key=lambda index: abs(index - caption_index))
            if chosen is None:
                blocks[caption_index] = replace(block, style="caption")  # type: ignore[arg-type]
                ctx.collector.add("orphan_caption", f"Подпись без изображения: {text}", "p")
                continue
            used_images.add(chosen)
            image = blocks[chosen]
            assert isinstance(image, Image)
            blocks[chosen] = replace(image, caption=text)
            to_remove.add(caption_index)

        for index in image_indices:
            if index in used_images:
                continue
            image = blocks[index]
            assert isinstance(image, Image)
            if not image.alt:
                ctx.collector.add(
                    "image_without_caption",
                    f"Изображение без подписи: {image.src.name}",
                    "img",
                    "info",
                )

    if to_remove:
        blocks[:] = [block for index, block in enumerate(blocks) if index not in to_remove]


def _iter_nested_blocks(blocks: list[Block]) -> Iterator[Block]:
    for block in blocks:
        yield block
        if isinstance(block, ListBlock):
            for item in block.items:
                yield from _iter_nested_blocks(item.blocks)


def build_document(soup: Any, source: Path, collector: WarningCollector) -> Document:
    clean_soup(soup)
    body = soup.body or soup
    ctx = _Context(source=source, collector=collector)
    blocks = _convert_children(body, ctx)
    _link_images_and_captions(blocks, ctx)

    h1_count = sum(
        1 for block in _iter_nested_blocks(blocks) if isinstance(block, Heading) and block.level == 1
    )
    if h1_count > 1:
        collector.add(
            "multiple_h1",
            f"В документе {h1_count} заголовков первого уровня",
            "file",
            "info",
        )

    flat = list(_iter_nested_blocks(blocks))
    stats = DocumentStats(
        headings=sum(isinstance(block, Heading) for block in flat),
        paragraphs=sum(isinstance(block, Paragraph) for block in flat),
        lists=sum(isinstance(block, ListBlock) for block in flat),
        tables=sum(isinstance(block, Table) for block in flat),
        images=sum(isinstance(block, Image) for block in flat),
    )
    return Document(
        title=source.stem,
        source=source,
        blocks=blocks,
        warnings=list(collector.items),
        stats=stats,
    )


def _positive_int(value: Any, default: int) -> int:
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return default
    return number if number > 0 else default
