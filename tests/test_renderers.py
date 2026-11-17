from __future__ import annotations

from pathlib import Path

from docx import Document as DocxDocument
from PIL import Image as PilImage
from pypdf import PdfReader

from html2doc.models import Document, Heading, Image, InlineRun, Paragraph, Table
from html2doc.options import ConvertOptions
from html2doc.render.docx import render_docx
from html2doc.render.markdown import render_markdown
from html2doc.render.pdf import render_pdf


def make_document(tmp_path: Path) -> Document:
    asset = tmp_path / "assets" / "test.jpg"
    asset.parent.mkdir(parents=True, exist_ok=True)
    PilImage.new("RGB", (80, 40), "white").save(asset)
    return Document(
        title="пример",
        source=tmp_path / "пример.htm",
        blocks=[
            Heading(1, (InlineRun("Заголовок"),)),
            Paragraph((InlineRun("Обычный ", ), InlineRun("текст", bold=True))),
            Table(
                rows=(
                    ((InlineRun("A", bold=True),), (InlineRun("B", bold=True),)),
                    ((InlineRun("1"),), (InlineRun("2"),)),
                ),
                header_rows=1,
            ),
            Image(
                src=asset,
                asset_path=Path("assets/test.jpg"),
                width_pt=60,
                height_pt=30,
                caption="Рисунок 1. Тест",
            ),
        ],
    )


def test_markdown_contains_table_and_image(tmp_path: Path) -> None:
    markdown = render_markdown(make_document(tmp_path))
    assert "# Заголовок" in markdown
    assert "| **A** | **B** |" in markdown
    assert "![Рисунок 1. Тест](assets/test.jpg)" in markdown
    assert "*Рисунок 1. Тест*" in markdown


def test_docx_contains_native_table_and_image(tmp_path: Path) -> None:
    document = make_document(tmp_path)
    render_docx(document, tmp_path, ConvertOptions(formats=("docx",)))
    result = DocxDocument(str(tmp_path / "пример.docx"))
    assert any(paragraph.text == "Заголовок" for paragraph in result.paragraphs)
    assert len(result.tables) == 1
    assert len(result.inline_shapes) == 1


def test_pdf_is_created(tmp_path: Path) -> None:
    document = make_document(tmp_path)
    render_pdf(document, tmp_path, ConvertOptions(formats=("pdf",)))
    target = tmp_path / "пример.pdf"
    assert target.read_bytes().startswith(b"%PDF")
    assert PdfReader(str(target)).get_num_pages() >= 1
