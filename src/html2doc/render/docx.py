"""Рендер DOCX через python-docx."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from docx import Document as DocxDocument
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from html2doc.assets import natural_size_pt
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

_FONT = "Times New Roman"


def _set_rfonts(element: Any) -> None:
    rpr = element.get_or_add_rPr()
    rfonts = rpr.rFonts
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
        rfonts.set(qn(f"w:{attribute}"), _FONT)


def _set_style_font(style: Any) -> None:
    style.font.name = _FONT
    _set_rfonts(style.element)


def _add_runs(
    paragraph: Any,
    runs: tuple[InlineRun, ...] | list[InlineRun],
    *,
    bold: bool = False,
    size_pt: float | None = None,
) -> None:
    for run in runs:
        item = paragraph.add_run(run.text)
        item.bold = run.bold or bold
        item.italic = run.italic
        item.underline = run.underline
        item.font.name = _FONT
        if size_pt is not None:
            item.font.size = Pt(size_pt)
        _set_rfonts(item._element)


def _set_table_borders(table: Any) -> None:
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    tbl_pr.append(borders)


def _repeat_header(row: Any) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def _render_table(document: Any, table: Table) -> Any:
    columns = max((len(row) for row in table.rows), default=0)
    if not columns:
        return None
    rendered = document.add_table(rows=len(table.rows), cols=columns)
    rendered.autofit = False
    _set_table_borders(rendered)
    if table.header_rows and rendered.rows:
        _repeat_header(rendered.rows[0])

    for row_index, row in enumerate(table.rows):
        for column_index, runs in enumerate(row):
            cell = rendered.cell(row_index, column_index)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            _add_runs(
                paragraph,
                runs,
                bold=bool(table.header_rows and row_index < table.header_rows),
                size_pt=9,
            )
    return rendered


def _render_image(
    document: Any,
    image: Image,
    output_dir: Path,
    options: ConvertOptions,
) -> Any:
    if image.missing:
        paragraph = document.add_paragraph()
        _add_runs(paragraph, (InlineRun(f"Изображение не найдено: {image.src}"),), size_pt=9)
        return paragraph

    path = output_dir / image.asset_path
    if not path.is_file():
        path = image.src
    if not path.is_file():
        paragraph = document.add_paragraph()
        _add_runs(paragraph, (InlineRun(f"Изображение не найдено: {image.src}"),), size_pt=9)
        return paragraph

    natural_width, _ = natural_size_pt(path)
    desired_width = image.width_pt or natural_width or options.image_max_width_pt
    width = Pt(min(desired_width, options.image_max_width_pt))
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.add_picture(str(path), width=width)
    if image.caption:
        caption = document.add_paragraph(style="Caption")
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _add_runs(caption, (InlineRun(image.caption),), size_pt=9)
    return paragraph


def _render_block(
    document: Any,
    block: Block,
    output_dir: Path,
    options: ConvertOptions,
    indent_pt: float = 0,
) -> Any:
    paragraph: Any | None = None
    if isinstance(block, Heading):
        paragraph = document.add_paragraph(style=f"Heading {block.level}")
        _add_runs(paragraph, block.runs)
    elif isinstance(block, Paragraph):
        style = "Caption" if block.style == "caption" else None
        paragraph = document.add_paragraph(style=style)
        _add_runs(paragraph, block.runs)
    elif isinstance(block, Table):
        return _render_table(document, block)
    elif isinstance(block, Image):
        return _render_image(document, block, output_dir, options)
    elif isinstance(block, ListBlock):
        for item in block.items:
            used_marker = False
            for child in item.blocks:
                if (
                    not used_marker
                    and isinstance(child, Paragraph)
                    and block.marker_style != "none"
                ):
                    style = "List Bullet" if block.marker_style == "bullet" else "List Number"
                    marker_paragraph = document.add_paragraph(style=style)
                    _add_runs(marker_paragraph, child.runs)
                    used_marker = True
                    continue
                _render_block(document, child, output_dir, options, indent_pt + 18)
        return None
    elif isinstance(block, PageBreak):
        document.add_page_break()
        return None

    if paragraph is not None and indent_pt:
        paragraph.paragraph_format.left_indent = Pt(indent_pt)
    return paragraph


def _setup_styles(document: Any) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2)
    section.right_margin = Cm(2)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)

    normal = document.styles["Normal"]
    _set_style_font(normal)
    normal.font.size = Pt(11)
    for level in (1, 2, 3):
        style = document.styles[f"Heading {level}"]
        _set_style_font(style)
        style.font.size = Pt({1: 18, 2: 14, 3: 12}[level])
    caption = document.styles["Caption"]
    _set_style_font(caption)
    caption.font.size = Pt(9)


def render_docx(document: Document, output_dir: Path, options: ConvertOptions) -> None:
    target = output_dir / f"{document.title}.docx"
    docx_document = DocxDocument()
    _setup_styles(docx_document)

    h1_seen = False
    for block in document.blocks:
        paragraph = _render_block(docx_document, block, output_dir, options)
        if (
            options.page_break_before_h1
            and isinstance(block, Heading)
            and block.level == 1
            and paragraph is not None
        ):
            if h1_seen:
                paragraph.paragraph_format.page_break_before = True
            h1_seen = True

    docx_document.save(str(target))
