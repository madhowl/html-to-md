import argparse
import hashlib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("artifacts"))
    parser.add_argument("--output", type=Path, default=Path("SHA256SUMS"))
    args = parser.parse_args()

    files = sorted(path for path in args.source.rglob("*") if path.is_file() and path.name != args.output.name)
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(args.source).as_posix()}"
        for path in files
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
