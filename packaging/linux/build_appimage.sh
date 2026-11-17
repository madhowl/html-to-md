#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
BUILD="$ROOT/build/linux"
DIST="$ROOT/dist"
PAYLOAD="$BUILD/payload"
APPDIR="$BUILD/html2doc.AppDir"
VERSION=$(cd "$ROOT" && uv run python -c "from html2doc import __version__; print(__version__)")
TOOL="${APPIMAGETOOL:-$BUILD/appimagetool.AppImage}"

rm -rf "$BUILD" "$APPDIR"
mkdir -p "$BUILD" "$DIST" "$PAYLOAD/fonts" "$APPDIR/usr/lib" "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/applications"

uv --directory "$ROOT" sync --frozen
uv --directory "$ROOT" run python "$ROOT/packaging/linux/collect_native.py" \
    --output "$PAYLOAD/native" \
    --library pango-1.0 \
    --library pangocairo-1.0 \
    --library pangoft2-1.0 \
    --library gobject-2.0 \
    --library glib-2.0 \
    --library gmodule-2.0 \
    --library gthread-2.0 \
    --library harfbuzz \
    --library harfbuzz-subset \
    --library freetype \
    --library fontconfig \
    --library cairo \
    --library cairo-gobject \
    --library expat \
    --library fribidi \
    --library graphite2 \
    --library png16 \
    --library ffi \
    --library pcre2-8 \
    --library xml2 \
    --library rsvg-2

cp "$ROOT/packaging/fonts.conf" "$PAYLOAD/fonts/fonts.conf"
for source_dir in /usr/share/fonts/truetype/dejavu /usr/share/fonts/truetype/liberation2 /usr/share/fonts/truetype/freefont; do
    if [ -d "$source_dir" ]; then
        cp -a "$source_dir/." "$PAYLOAD/fonts/"
    fi
done

export HTML2DOC_PAYLOAD_DIR="$PAYLOAD"
export HTML2DOC_ICON="$ROOT/packaging/icons/icon.png"
export HTML2DOC_ONEFILE=0
uv --directory "$ROOT" run pyinstaller "$ROOT/packaging/pyinstaller.spec" \
    --noconfirm \
    --distpath "$BUILD/dist" \
    --workpath "$BUILD/work" \
    --log-level WARN

cp -a "$BUILD/dist/html2doc" "$APPDIR/usr/lib/html2doc"
cp "$ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp "$ROOT/packaging/linux/html2doc.desktop" "$APPDIR/html2doc.desktop"
cp "$ROOT/packaging/linux/html2doc.desktop" "$APPDIR/usr/share/applications/html2doc.desktop"
cp "$ROOT/packaging/icons/icon.png" "$APPDIR/html2doc.png"
cp "$ROOT/packaging/icons/icon.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/html2doc.png"

if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$APPDIR/html2doc.desktop"
fi

if [ ! -f "$TOOL" ]; then
    curl -fL --retry 3 \
        -o "$TOOL" \
        https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$TOOL"
fi

ARCH=x86_64 "$TOOL" --appimage-extract-and-run "$APPDIR" "$DIST/html2doc-${VERSION}-x86_64.AppImage"
echo "Готово: $DIST/html2doc-${VERSION}-x86_64.AppImage"
