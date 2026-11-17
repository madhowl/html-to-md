"""Исключения конвертера."""


class ConversionError(Exception):
    """Фатальная ошибка конвертации одного файла."""


class ArchiveValidationError(ConversionError):
    """Некорректный ZIP-архив, загруженный через Web UI."""
