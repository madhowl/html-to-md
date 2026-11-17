"""Command-line интерфейс html2doc."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from html2doc.options import ConvertOptions
from html2doc.pipeline import convert_batch

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


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

    uvicorn.run("html2doc.web.app:app", host=host, port=port)


if __name__ == "__main__":
    app()
