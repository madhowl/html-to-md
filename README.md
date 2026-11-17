# html2doc

Конвертер HTML/HTM в Markdown, PDF и DOCX с общим ядром и тремя интерфейсами: CLI, Qt6 GUI и Web UI.

## Установка

```bash
uv sync
```

Требуется Python 3.12+. Для PDF через WeasyPrint нужны системные библиотеки Pango/Cairo/HarfBuzz; portable-сборки содержат их в себе.

## Использование

### CLI

```bash
uv run html2doc convert ./лекции --to md,pdf,docx --out ./output
uv run html2doc convert ./лекции/лекция-1.htm --to md
uv run html2doc gui
uv run html2doc web --host 127.0.0.1 --port 8000
```

### Qt6 GUI

```bash
uv run html2doc gui
```

Выберите файлы или каталог, форматы и каталог результата, затем нажмите «Конвертировать».

### Web UI

```bash
uv run html2doc web
```

Откройте `http://127.0.0.1:8000`, загрузите ZIP с HTML-файлами и изображениями, дождитесь завершения и скачайте ZIP с результатами.

## Структура результата

```text
output/<имя_файла>/
  <имя_файла>.md
  <имя_файла>.pdf
  <имя_файла>.docx
  assets/...
  conversion-report.json
```

## Особенности

- Поддерживаются HTML 4, UTF-8 с BOM и кириллические пути.
- Таблицы преобразуются в GFM-таблицы Markdown или нативные таблицы DOCX/PDF.
- Изображения копируются в `assets/` и встраиваются в PDF/DOCX.
- Подписи вида «Рисунок N» связываются с ближайшими изображениями в пределах логического раздела.
- Артефакты OCR записываются в `conversion-report.json`.

## Ограничения

Текст внутри растровых изображений не распознаётся. Исходные повреждения OCR не восстанавливаются — только фиксируются в отчёте. Более подробные требования приведены в `tz.md`.

## Проверки

```bash
uv run pytest
uv run ruff check
uv run mypy src
uv run html2doc selftest
```

## Portable-сборки

Готовые артефакты сборятся в GitHub Actions и публикуются по тегу `vX.Y.Z`:

- `html2doc-<версия>-x86_64.AppImage` — Linux;
- `html2doc-<версия>-windows-x86_64.exe` — Windows onefile;
- `html2doc-<версия>-windows-x86_64-portable.zip` — Windows onedir;
- `SHA256SUMS` — контрольные суммы.

Локальная сборка AppImage:

```bash
bash packaging/linux/build_appimage.sh
```

Локальная сборка Windows из PowerShell на Windows:

```powershell
pwsh packaging/windows/build_exe.ps1 -Mode both
```

Portable-бинарник без аргументов открывает GUI. CLI доступен через явные команды:

```bash
html2doc convert ./лекции --to md,pdf,docx --out ./output
html2doc gui
html2doc web --host 127.0.0.1 --port 8000
html2doc selftest
html2doc --version
```

## GitFlow

- `main` — стабильные релизы, только через PR из `release/*` и `hotfix/*`.
- `develop` — интеграционная ветка, только через PR из `feature/*`.
- `feature/*` — новые возможности.
- `release/*` — подготовка версии.
- `hotfix/*` — срочные исправления с сразу двумя PR: в `main` и `develop`.
- Коммиты — Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`, `chore:`, `refactor:`).
- Релизы создаются тегом `vX.Y.Z` и публикуются workflow `Release`.
