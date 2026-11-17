from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from html2doc.cli import app


def test_cli_converts_single_file(tmp_path: Path) -> None:
    source = tmp_path / "лекция.htm"
    source.write_text(
        "<html><body><h1>Тест</h1><p>Текст</p></body></html>",
        encoding="utf-8-sig",
    )
    output = tmp_path / "out"

    result = CliRunner().invoke(app, ["convert", str(source), "--to", "md", "--out", str(output)])

    assert result.exit_code == 0, result.output
    assert (output / "лекция" / "лекция.md").is_file()
    assert (output / "лекция" / "conversion-report.json").is_file()
