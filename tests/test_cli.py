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


def test_cli_version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "0.1.0"


def test_cli_selftest() -> None:
    result = CliRunner().invoke(app, ["selftest"])

    assert result.exit_code == 0, result.output
    assert "selftest: готово" in result.output
