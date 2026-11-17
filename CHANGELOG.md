# Changelog

Все значимые изменения фиксируются в этом файле. Формат основан на Keep a Changelog, версии следуют Semantic Versioning.

## [0.1.2]

### Fixed

- Удалены недоступные в Ubuntu 22.04 и MSYS2 пакеты из workflows.
- Поиск MSYS2 в Windows-сборке и передача путей DLL/шрифтов в PyInstaller.
- Возвращаемое значение `Invoke-Build` больше не затирается выводом PyInstaller.
- Исправлен путь к onefile `.exe` и проверка наличия DLL natives.
- UTF-8 вывод консоли Windows для CLI и `selftest`.

## [0.1.1]

### Fixed

- CI больше не падает при отсутствии необязательной библиотеки `harfbuzz-subset`.

## [0.1.0]

### Added

- Конвертация HTML/HTM в Markdown, PDF и DOCX с общим pipeline.
- CLI, Qt6 GUI и Web UI с загрузкой ZIP.
- Portable-сборки Linux AppImage и Windows onefile/onedir ZIP.
- GitHub Actions для тестов, сборки и релизов по тегам.
