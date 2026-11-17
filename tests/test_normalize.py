from __future__ import annotations

from pathlib import Path

from PIL import Image as PilImage

from html2doc.models import Heading, Image, ListBlock, Paragraph, Table
from html2doc.normalize import build_document
from html2doc.reader import read_html
from html2doc.report import WarningCollector


def build(tmp_path: Path, markup: str, name: str = "sample.htm"):
    path = tmp_path / name
    path.write_bytes("\ufeff".encode("utf-8") + markup.replace("\n", "\r\n").encode("utf-8"))
    collector = WarningCollector()
    document = build_document(read_html(path, collector), path, collector)
    return document, collector


def test_bom_empty_anchor_and_title_from_filename(tmp_path: Path) -> None:
    document, _ = build(
        tmp_path,
        "<html><head><title>Сканированное изображение</title></head>"
        '<body><h1><a name="bookmark0"></a><span>Заголовок</span></h1>'
        "<p><span>Текст</span></p></body></html>",
        name="лекция-1.htm",
    )
    assert document.title == "лекция-1"
    assert isinstance(document.blocks[0], Heading)
    assert document.blocks[0].runs[0].text == "Заголовок"


def test_heading_inside_li_and_double_br_are_split(tmp_path: Path) -> None:
    document, _ = build(
        tmp_path,
        "<body><ul style='list-style:none;'><li><h2>1. Раздел<br><br>1.1. Подраздел</h2>"
        "<p>Текст</p></li></ul></body>",
    )
    headings = [block for block in document.blocks if isinstance(block, Heading)]
    assert [block.runs[0].text for block in headings] == ["1. Раздел", "1.1. Подраздел"]
    assert all(not isinstance(block, ListBlock) for block in document.blocks)
    assert any(isinstance(block, Paragraph) for block in document.blocks)


def test_inline_styles_are_preserved(tmp_path: Path) -> None:
    document, _ = build(
        tmp_path,
        "<body><p><span style='font-weight:bold;'>Жирный</span> "
        "<span style='font-style:italic;'>курсив</span> "
        "<span style='text-decoration:underline;'>подчёркнутый</span></p></body>",
    )
    paragraph = next(block for block in document.blocks if isinstance(block, Paragraph))
    by_text = {run.text.strip(): run for run in paragraph.runs if run.text.strip()}
    assert by_text["Жирный"].bold
    assert by_text["курсив"].italic
    assert by_text["подчёркнутый"].underline


def test_manual_marker_is_not_duplicated(tmp_path: Path) -> None:
    document, collector = build(
        tmp_path,
        "<body><ul style='list-style:none;'><li>• первый</li><li>• второй</li></ul></body>",
    )
    list_block = next(block for block in document.blocks if isinstance(block, ListBlock))
    assert list_block.marker_style == "none"
    assert "• первый" in list_block.items[0].blocks[0].runs[0].text  # type: ignore[index]
    assert any(item.code == "manual_marker" for item in collector.items)


def test_table_with_colspan_uses_fallback(tmp_path: Path) -> None:
    document, collector = build(
        tmp_path,
        "<body><table border='1'><tr><td colspan='2'><b>Шапка</b></td></tr>"
        "<tr><td>A</td><td></td></tr></table></body>",
    )
    table = next(block for block in document.blocks if isinstance(block, Table))
    assert table.html_fallback is not None
    assert "colspan=\"2\"" in table.html_fallback
    assert any(item.code == "colspan_table" for item in collector.items)


def test_image_caption_is_linked_before_image(tmp_path: Path) -> None:
    image_path = tmp_path / "рисунок.jpg"
    PilImage.new("RGB", (40, 20), "white").save(image_path)
    document, collector = build(
        tmp_path,
        "<body><p><span style='font-style:italic;'>Рисунок 1. Тест</span></p>"
        '<div><img src="рисунок.jpg" alt=""></div></body>',
    )
    image = next(block for block in document.blocks if isinstance(block, Image))
    assert image.caption == "Рисунок 1. Тест"
    assert not any(isinstance(block, Paragraph) and "Рисунок 1" in "".join(run.text for run in block.runs) for block in document.blocks)
    assert not any(item.code == "orphan_caption" for item in collector.items)
