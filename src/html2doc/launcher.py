"""Точка входа для portable-сборок: GUI по умолчанию, CLI через аргументы."""

from __future__ import annotations

import ctypes
import os
import sys

from html2doc.paths import bundle_dir, is_frozen


def _prepare_environment() -> None:
    if not is_frozen():
        return

    root = bundle_dir()
    candidates = [root, root / "native", root / "qt_plugins", root / "fonts"]
    for candidate in candidates:
        if not candidate.is_dir():
            continue
        value = str(candidate)
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(value)
        os.environ["PATH"] = value + os.pathsep + os.environ.get("PATH", "")

    font_dir = root / "fonts"
    if font_dir.is_dir():
        config = font_dir / "fonts.conf"
        if config.is_file():
            os.environ.setdefault("FONTCONFIG_FILE", str(config))
        os.environ.setdefault("FONTCONFIG_PATH", str(font_dir))

    qt_plugins = root / "qt_plugins"
    if qt_plugins.is_dir():
        os.environ.setdefault("QT_PLUGIN_PATH", str(qt_plugins))
        platforms = qt_plugins / "platforms"
        if platforms.is_dir():
            os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(platforms))


def _detach_console() -> None:
    if sys.platform != "win32" or not is_frozen():
        return
    windll = getattr(ctypes, "windll", None)
    if windll is not None:
        windll.kernel32.FreeConsole()


def main() -> None:
    _prepare_environment()
    args = sys.argv[1:]

    if not args:
        _detach_console()
        from html2doc.gui.main_window import run_gui

        run_gui()
        return

    if args == ["--version"]:
        from html2doc import __version__

        print(__version__)
        return

    from html2doc.cli import app

    if args[0] in {"gui", "web"} or str(args[0]).startswith("-"):
        _detach_console()
    app(args)


if __name__ == "__main__":
    main()
