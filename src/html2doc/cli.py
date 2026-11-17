"""Command-line интерфейс html2doc."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import typer
from rich.console import Console

from html2doc import __version__
from html2doc.options import ConvertOptions
from html2doc.paths import resource_path
from html2doc.pipeline import convert_batch

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()

_SELFTEST_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def _version_callback(value: bool) -> None:
    if not value:
        return
    typer.echo(__version__)
    raise typer.Exit()


@app.callback()
def main(version: bool = typer.Option(
    False,
    "--version",
    callback=_version_callback,
    is_eager=True,
    help="Показать версию.",
)) -> None:
    """html2doc."""


@app.command()
def convert(
    path: Path = typer.Argument(..., help="Файл .htm/.html или каталог с исходниками"),
    to: str = typer.Option("md,pdf,docx", "--to", help="Форматы через запятую: md,pdf,docx"),
    out: Path = typer.Option(Path("output"), "--out", help="Каталог результатов"),
    no_page_break: bool = typer.Option(False, "--no-page-break", help="Не разрывать страницу перед h1"),
    no_assets: bool = typer.Option(False, "--no-assets", help="Не копировать изображения"),
    no_report: bool = typer.Option(False, "--no-report", help="Не писать conversion-report.json"),
    no_recursive: bool = typer.Option(False, "--no-recursive", help="Не обходить подкаталоги"),
) -> None:
    """Конвертировать HTML/HTM в выбранные форматы."""
    try:
        options = ConvertOptions.from_string(
            to,
            page_break_before_h1=not no_page_break,
            copy_assets=not no_assets,
            include_report=not no_report,
            recursive=not no_recursive,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    def on_progress(current: int, total: int, source: Path, ok: bool) -> None:
        status = "[green]ok[/green]" if ok else "[red]error[/red]"
        console.print(f"[{current}/{total}] {source.name}: {status}")

    results = convert_batch(path, out, options, on_progress)
    errors = sum(result.error is not None for result in results)
    warnings = sum(len(result.warnings) for result in results)
    console.print(
        f"Обработано: {len(results)}, ошибок: {errors}, предупреждений: {warnings}, выход: {out}"
    )
    if errors:
        raise typer.Exit(code=1)


@app.command()
def gui() -> None:
    """Запустить десктопное Qt6-приложение."""
    from html2doc.gui.main_window import run_gui

    run_gui()


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Адрес прослушивания"),
    port: int = typer.Option(8000, "--port", help="Порт"),
) -> None:
    """Запустить веб-сервер с загрузкой ZIP."""
    import uvicorn

    from html2doc.web.app import app as web_app

    uvicorn.run(web_app, host=host, port=port)


@app.command()
def selftest() -> None:
    """Проверить конвертацию и наличие ресурсов bundle."""
    import base64

    with tempfile.TemporaryDirectory(prefix="html2doc-selftest-") as tmp:
        root = Path(tmp)
        source_dir = root / "source"
        source_dir.mkdir()
        (source_dir / "images").mkdir()
        (source_dir / "images" / "pixel.png").write_bytes(base64.b64decode(_SELFTEST_PNG))
        source = source_dir / "selftest.htm"
        source.write_text(
            "<html><body><h1>Проверка</h1><p>Тестовый документ.</p>"
            "<table><tr><th>Колонка</th></tr><tr><td>Значение</td></tr></table>"
            '<img src="images/pixel.png" alt=""></body></html>',
            encoding="utf-8",
        )

        results = convert_batch(source_dir, root / "output", ConvertOptions())
        failed = [result for result in results if not result.ok or len(result.files) != 3]
        if failed:
            console.print(f"[red]selftest: конвертация не удалась: {failed[0].error}[/red]")
            raise typer.Exit(code=1)

        markdown = next(path for path in results[0].files if path.suffix == ".md")
        pdf = next(path for path in results[0].files if path.suffix == ".pdf")
        docx = next(path for path in results[0].files if path.suffix == ".docx")
        checks = {
            "templates": resource_path("web/templates/index.html").is_file(),
            "static": resource_path("web/static/app.js").is_file(),
            "markdown": "Проверка" in markdown.read_text(encoding="utf-8"),
            "pdf": pdf.read_bytes().startswith(b"%PDF"),
            "docx": zipfile.is_zipfile(docx),
        }
        missing = [name for name, ok in checks.items() if not ok]
        if missing:
            console.print(f"[red]selftest: не пройдены проверки: {', '.join(missing)}[/red]")
            raise typer.Exit(code=1)
        console.print("[green]selftest: готово[/green]")


if __name__ == "__main__":
    app()
