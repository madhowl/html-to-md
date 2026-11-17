"""Нативное Qt6-приложение html2doc."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from html2doc.gui.worker import ConversionWorker
from html2doc.options import ConvertOptions
from html2doc.pipeline import ConversionResult


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[Path] = []
        self.results: list[ConversionResult] = []
        self.worker: ConversionWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("html2doc — конвертер HTML в Markdown / PDF / DOCX")
        self.resize(920, 680)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        source_group = QGroupBox("Исходники")
        source_layout = QHBoxLayout(source_group)
        self.path_edit = QLabel("Файлы не выбраны")
        self.path_edit.setWordWrap(True)
        source_layout.addWidget(self.path_edit, stretch=1)
        files_button = QPushButton("Выбрать файлы…")
        files_button.clicked.connect(self._choose_files)
        dir_button = QPushButton("Выбрать каталог…")
        dir_button.clicked.connect(self._choose_directory)
        source_layout.addWidget(files_button)
        source_layout.addWidget(dir_button)
        layout.addWidget(source_group)

        format_group = QGroupBox("Форматы результата")
        format_layout = QHBoxLayout(format_group)
        self.md_check = QCheckBox("Markdown")
        self.pdf_check = QCheckBox("PDF")
        self.docx_check = QCheckBox("DOCX")
        for checkbox in (self.md_check, self.pdf_check, self.docx_check):
            checkbox.setChecked(True)
            format_layout.addWidget(checkbox)
        layout.addWidget(format_group)

        output_group = QGroupBox("Каталог результата")
        output_layout = QHBoxLayout(output_group)
        self.output_edit = QLabel(str(Path("output").resolve()))
        output_layout.addWidget(self.output_edit, stretch=1)
        output_button = QPushButton("Изменить…")
        output_button.clicked.connect(self._choose_output)
        output_layout.addWidget(output_button)
        layout.addWidget(output_group)

        options_group = QGroupBox("Опции")
        options_layout = QHBoxLayout(options_group)
        self.break_check = QCheckBox("Разрыв страницы перед h1")
        self.assets_check = QCheckBox("Копировать изображения")
        self.report_check = QCheckBox("Сохранять отчёт")
        self.assets_check.setChecked(True)
        self.report_check.setChecked(True)
        for checkbox in (self.break_check, self.assets_check, self.report_check):
            options_layout.addWidget(checkbox)
        layout.addWidget(options_group)

        actions = QHBoxLayout()
        self.start_button = QPushButton("Конвертировать")
        self.start_button.clicked.connect(self._start)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel)
        open_button = QPushButton("Открыть результат")
        open_button.clicked.connect(self._open_output)
        actions.addWidget(self.start_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(open_button)
        layout.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log_table = QTableWidget(0, 3)
        self.log_table.setHorizontalHeaderLabels(["Уровень", "Файл", "Сообщение"])
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.log_table.setAlternatingRowColors(True)
        layout.addWidget(self.log_table, stretch=1)

    def _choose_files(self) -> None:
        selected, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите HTML-файлы",
            filter="HTML (*.htm *.html);;Все файлы (*)",
        )
        if selected:
            self.inputs = [Path(item) for item in selected]
            self.path_edit.setText("; ".join(item.name for item in self.inputs))

    def _choose_directory(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Выберите каталог с лекциями")
        if selected:
            self.inputs = [Path(selected)]
            self.path_edit.setText(selected)

    def _choose_output(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Каталог результата")
        if selected:
            self.output_edit.setText(selected)

    def _options(self) -> ConvertOptions | None:
        formats = []
        if self.md_check.isChecked():
            formats.append("md")
        if self.pdf_check.isChecked():
            formats.append("pdf")
        if self.docx_check.isChecked():
            formats.append("docx")
        try:
            return ConvertOptions(
                tuple(formats),
                page_break_before_h1=self.break_check.isChecked(),
                copy_assets=self.assets_check.isChecked(),
                include_report=self.report_check.isChecked(),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка", str(exc))
            return None

    def _start(self) -> None:
        if not self.inputs:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите файлы или каталог")
            return
        options = self._options()
        if options is None:
            return

        self.results = []
        self.log_table.setRowCount(0)
        self.progress.setValue(0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        source: Path | list[Path] = self.inputs[0] if len(self.inputs) == 1 else self.inputs
        self.worker = ConversionWorker(source, Path(self.output_edit.text()), options, self)
        self.worker.progress.connect(self._on_progress)
        self.worker.log.connect(self._on_log)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.start()

    def _cancel(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.cancel_button.setEnabled(False)

    def _on_progress(self, current: int, total: int, source: str, ok: bool) -> None:
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(current)
        status = "готово" if ok else "ошибка"
        self._append_log("info", Path(source).name, f"{current}/{total} — {status}")

    def _on_log(self, level: str, source: str, message: str) -> None:
        self._append_log(level, source, message)

    def _append_log(self, level: str, source: str, message: str) -> None:
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        self.log_table.setItem(row, 0, QTableWidgetItem(level))
        self.log_table.setItem(row, 1, QTableWidgetItem(source))
        self.log_table.setItem(row, 2, QTableWidgetItem(message))

    def _on_finished(self, results: list[ConversionResult]) -> None:
        self.results = results
        self.progress.setValue(self.progress.maximum())
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        errors = sum(result.error is not None for result in results)
        QMessageBox.information(
            self,
            "Конвертация завершена",
            f"Обработано файлов: {len(results)}\nОшибок: {errors}",
        )

    def _open_output(self) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(self.output_edit.text()))


def run_gui() -> None:
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
