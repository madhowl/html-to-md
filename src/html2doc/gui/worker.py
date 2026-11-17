"""Фоновая конвертация для Qt6 GUI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from html2doc.models import ConversionWarning
from html2doc.options import ConvertOptions
from html2doc.pipeline import ConversionResult, convert_batch


class ConversionWorker(QThread):
    progress = Signal(int, int, str, bool)
    log = Signal(str, str, str)
    finished_ok = Signal(object)

    def __init__(
        self,
        inputs: Path | list[Path],
        output_dir: Path,
        options: ConvertOptions,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.inputs = inputs
        self.output_dir = output_dir
        self.options = options
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _emit_warnings(self, result: ConversionResult) -> None:
        warning: ConversionWarning
        for warning in result.warnings:
            self.log.emit(warning.severity, result.source.name, warning.message)
        if result.error:
            self.log.emit("error", result.source.name, result.error)

    def run(self) -> None:
        def on_progress(current: int, total: int, source: Path, ok: bool) -> bool:
            self.progress.emit(current, total, str(source), ok)
            return not self._cancelled

        results = convert_batch(self.inputs, self.output_dir, self.options, on_progress)
        for result in results:
            self._emit_warnings(result)
        self.finished_ok.emit(results)
