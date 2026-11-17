"""Разрешение, копирование и измерение изображений."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from urllib.parse import unquote, urlparse

from PIL import Image as PilImage
from PIL import UnidentifiedImageError

_LENGTH_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(pt|px|mm|in|%)?\s*$", re.IGNORECASE)
_UNIT_TO_PT = {"pt": 1.0, "px": 0.75, "mm": 2.8346456693, "in": 72.0}


def parse_css_length(value: str | None) -> float | None:
    if not value:
        return None
    match = _LENGTH_RE.match(value)
    if not match:
        return None
    number = float(match.group(1))
    unit = (match.group(2) or "px").lower()
    if unit == "%":
        return None
    return round(number * _UNIT_TO_PT[unit], 2)


def style_lengths(style: str | None) -> tuple[float | None, float | None]:
    if not style:
        return None, None
    declarations: dict[str, str] = {}
    for part in style.split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        declarations[key.strip().lower()] = value.strip()
    return parse_css_length(declarations.get("width")), parse_css_length(declarations.get("height"))


def resolve_image(source: Path, src: str) -> Path | None:
    if not src:
        return None
    parsed = urlparse(src)
    if parsed.scheme or parsed.netloc or src.startswith("//"):
        return None
    path = Path(unquote(parsed.path))
    if path.is_absolute() or ".." in path.parts:
        return None
    candidate = (source.parent / path).resolve()
    if candidate.is_file():
        return candidate
    return None


def destination_for_image(source: Path, resolved: Path, asset_root: Path = Path("assets")) -> Path:
    try:
        relative = resolved.relative_to(source.parent)
    except ValueError:
        relative = Path(resolved.name)
    safe_parts = [
        part for part in relative.parts if part not in {"", ".", ".."} and not part.startswith("/")
    ]
    return asset_root.joinpath(*safe_parts or [resolved.name])


def natural_size_pt(path: Path) -> tuple[float | None, float | None]:
    try:
        with PilImage.open(path) as image:
            width, height = image.size
    except (OSError, UnidentifiedImageError, ValueError):
        return None, None
    return round(width * 0.75, 2), round(height * 0.75, 2)


def copy_assets(images, output_dir: Path) -> int:
    copied = 0
    seen: set[Path] = set()
    for image in images:
        if image.missing:
            continue
        destination = output_dir / image.asset_path
        resolved_destination = destination.resolve()
        if resolved_destination in seen:
            continue
        if not destination.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image.src, destination)
        seen.add(resolved_destination)
        copied += 1
    return copied
