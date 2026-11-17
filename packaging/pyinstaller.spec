import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPEC).resolve().parent.parent
ONEFILE = os.environ.get("HTML2DOC_ONEFILE", "0") == "1"
PAYLOAD_DIR = os.environ.get("HTML2DOC_PAYLOAD_DIR")
ICON = os.environ.get("HTML2DOC_ICON")

datas = [
    (str(ROOT / "src" / "html2doc" / "web" / "templates"), "web/templates"),
    (str(ROOT / "src" / "html2doc" / "web" / "static"), "web/static"),
]

if PAYLOAD_DIR:
    for name in ("native", "fonts", "qt_plugins"):
        source = Path(PAYLOAD_DIR) / name
        if source.is_dir():
            datas.append((str(source), name))

if ICON and not Path(ICON).is_file():
    ICON = None

hiddenimports = [
    "html2doc.cli",
    "html2doc.gui.main_window",
    "html2doc.web.app",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
]
for package in ("weasyprint", "typer", "rich", "fastapi", "uvicorn", "lxml", "PIL", "docx"):
    hiddenimports.extend(collect_submodules(package))

a = Analysis(
    [str(ROOT / "src" / "html2doc" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=list(dict.fromkeys(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="html2doc",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=True,
        icon=ICON,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="html2doc",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=True,
        icon=ICON,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=False,
        name="html2doc",
    )
