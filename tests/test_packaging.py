from __future__ import annotations

import sys

from html2doc import __version__
from html2doc.launcher import main
from html2doc.paths import is_frozen, resource_path


def test_resource_path_points_to_packaged_assets() -> None:
    assert resource_path("web/templates/index.html").is_file()
    assert resource_path("web/static/app.js").is_file()
    assert is_frozen() is False


def test_launcher_version(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["html2doc", "--version"])

    main()

    assert capsys.readouterr().out.strip() == __version__
