from __future__ import annotations

from pathlib import Path

import pytest

from html2doc.options import ConvertOptions
from html2doc.pipeline import convert_batch

SAMPLES = Path(__file__).resolve().parents[1] / "лекции"
pytestmark = pytest.mark.skipif(not SAMPLES.is_dir(), reason="Каталог образцов не найден")


def test_key_samples_convert_to_all_formats(tmp_path: Path) -> None:
    inputs = [SAMPLES / "лекция-1.htm", SAMPLES / "чек-листы.htm"]
    results = convert_batch(inputs, tmp_path / "out", ConvertOptions())
    assert len(results) == 2
    for result in results:
        assert result.ok, result.error
        assert (result.output_dir / f"{result.source.stem}.md").is_file()
        assert (result.output_dir / f"{result.source.stem}.pdf").is_file()
        assert (result.output_dir / f"{result.source.stem}.docx").is_file()
        assert (result.output_dir / "conversion-report.json").is_file()


def test_all_samples_convert_to_markdown_and_copy_images(tmp_path: Path) -> None:
    results = convert_batch(SAMPLES, tmp_path / "out", ConvertOptions(formats=("md",)))
    assert len(results) == 13
    assert all(result.ok for result in results), [result.error for result in results]
    copied = 0
    for result in results:
        assets = result.output_dir / "assets"
        if assets.is_dir():
            copied += sum(1 for path in assets.rglob("*") if path.is_file())
    assert copied == 58
