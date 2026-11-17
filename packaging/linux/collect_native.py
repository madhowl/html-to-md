import argparse
import ctypes.util
import shutil
import subprocess
from pathlib import Path

SKIP_PREFIXES = (
    "libc.so",
    "libm.so",
    "libpthread.so",
    "libdl.so",
    "librt.so",
    "ld-linux",
    "linux-vdso",
    "linux-gate",
)


def ldconfig_entries() -> dict[str, Path]:
    result = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, check=False)
    entries: dict[str, Path] = {}
    for line in result.stdout.splitlines():
        if "=>" not in line:
            continue
        name, target = line.split("=>", 1)
        name = name.split("(", 1)[0].strip()
        path = Path(target.split("(", 1)[0].strip())
        if path.is_file():
            entries[name.strip()] = path
    return entries


def resolve_library(name: str, entries: dict[str, Path]) -> Path:
    for key, path in entries.items():
        if key == name or key.startswith(f"{name}."):
            return path
    found = ctypes.util.find_library(name)
    if found:
        if found in entries:
            return entries[found]
        path = Path(found)
        if path.is_file():
            return path
    raise RuntimeError(f"Не найдена библиотека: {name}")


def linked_libraries(path: Path) -> list[Path]:
    result = subprocess.run(["ldd", str(path)], capture_output=True, text=True, check=False)
    found: list[Path] = []
    for line in result.stdout.splitlines():
        if "=>" in line:
            candidate = Path(line.split("=>", 1)[1].split("(", 1)[0].strip())
        elif line.strip().startswith("/"):
            candidate = Path(line.strip().split()[0])
        else:
            continue
        if candidate.is_file() and candidate not in found:
            found.append(candidate)
    return found


def should_skip(path: Path) -> bool:
    return path.name.startswith(SKIP_PREFIXES)


def copy_library(path: Path, output: Path, seen: set[Path], alias: str | None = None) -> None:
    real = path.resolve()
    if real in seen or should_skip(real):
        return
    target = output / real.name
    shutil.copy2(real, target, follow_symlinks=True)
    if alias and alias != real.name:
        link = output / alias
        if not link.exists():
            link.symlink_to(real.name)
    seen.add(real)
    for linked in linked_libraries(real):
        copy_library(linked, output, seen)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--library", action="append", required=True)
    args = parser.parse_args()

    output: Path = args.output
    output.mkdir(parents=True, exist_ok=True)
    entries = ldconfig_entries()
    seen: set[Path] = set()
    for name in args.library:
        path = resolve_library(name, entries)
        copy_library(path, output, seen, alias=path.name)
    print(f"Скопировано библиотек: {len(seen)}")


if __name__ == "__main__":
    main()
