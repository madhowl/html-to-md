"""Публичный API конвертации."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from html2doc.assets import copy_assets
from html2doc.errors import ConversionError
from html2doc.models import ConversionWarning
from html2doc.normalize import build_document
from html2doc.options import ConvertOptions
from html2doc.reader import read_html
from html2doc.render.docx import render_docx
from html2doc.render.markdown import render_markdown
from html2doc.render.pdf import render_pdf
from html2doc.report import WarningCollector, write_report

HTML_SUFFIXES = {".htm", ".html"}
ProgressCallback = Callable[[int, int, Path, bool], bool | None]


@dataclass(slots=True)
class ConversionResult:
    source: Path
    output_dir: Path
    files: list[Path] = field(default_factory=list)
    warnings: list[ConversionWarning] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def as_dict(self) -> dict[str, object]:
        return {
            "source": self.source.name,
            "output_dir": self.output_dir.name,
            "files": [path.name for path in self.files],
            "warnings": [item.as_dict() for item in self.warnings],
            "error": self.error,
        }


def _natural_key(path: Path) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
        if part
    ]


def discover_inputs(path: Path, recursive: bool = True) -> list[Path]:
    path = path.resolve()
    if path.is_file():
        if path.suffix.lower() not in HTML_SUFFIXES:
            raise ConversionError(f"Ожидался файл .htm или .html, получен: {path}")
        return [path]
    if not path.is_dir():
        raise ConversionError(f"Путь не существует: {path}")

    iterator = path.rglob("*") if recursive else path.glob("*")
    files = [
        item.resolve()
        for item in iterator
        if item.is_file() and item.suffix.lower() in HTML_SUFFIXES
    ]
    return sorted(files, key=_natural_key)


def _collect_images(blocks):
    from html2doc.models import Image, ListBlock

    for block in blocks:
        if isinstance(block, Image):
            yield block
        elif isinstance(block, ListBlock):
            for item in block.items:
                yield from _collect_images(item.blocks)


def convert_file(source: Path, output_root: Path, options: ConvertOptions) -> ConversionResult:
    source = source.resolve()
    output_dir = output_root.resolve() / source.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    collector = WarningCollector()

    soup = read_html(source, collector)
    document = build_document(soup, source, collector)

    if options.copy_assets:
        try:
            document.stats.copied_assets = copy_assets(
                list(_collect_images(document.blocks)), output_dir
            )
        except OSError as exc:
            collector.add("asset_copy_error", f"Ошибка копирования изображений: {exc}", "assets")

    files: list[Path] = []
    error: str | None = None
    try:
        if "md" in options.formats:
            target = output_dir / f"{document.title}.md"
            target.write_text(render_markdown(document), encoding="utf-8")
            files.append(target)
        if "pdf" in options.formats:
            render_pdf(document, output_dir, options)
            files.append(output_dir / f"{document.title}.pdf")
        if "docx" in options.formats:
            render_docx(document, output_dir, options)
            files.append(output_dir / f"{document.title}.docx")
    except Exception as exc:
        error = str(exc)
        collector.add("render_error", error, "render", "error")

    document.warnings = list(collector.items)
    if options.include_report:
        write_report(
            output_dir / "conversion-report.json",
            source=source.name,
            formats=options.formats,
            warnings=document.warnings,
            stats=document.stats.as_dict(),
        )

    return ConversionResult(source, output_dir, files, document.warnings, error)


def convert_batch(
    path: Path | list[Path],
    output_root: Path,
    options: ConvertOptions,
    progress_callback: ProgressCallback | None = None,
) -> list[ConversionResult]:
    inputs = [item.resolve() for item in path] if isinstance(path, list) else discover_inputs(path, options.recursive)
    results: list[ConversionResult] = []
    total = len(inputs)

    for index, source in enumerate(inputs, start=1):
        try:
            result = convert_file(source, output_root, options)
        except Exception as exc:
            collector = WarningCollector()
            collector.add("conversion_error", str(exc), "file", "error")
            result = ConversionResult(
                source,
                output_root.resolve() / source.stem,
                [],
                list(collector.items),
                str(exc),
            )
        results.append(result)

        if progress_callback is not None:
            should_continue = progress_callback(index, total, source, result.ok)
            if should_continue is False:
                break
    return results
