from __future__ import annotations

import argparse
from pathlib import Path

SUSPICIOUS_TOKENS = ("\u00c3", "\u00c2", "\ufffd")
TEXT_EXTENSIONS = {".md", ".txt"}
SPECIAL_NAMES = {"README", "README.md", "HANDOFF.md", "CHANGELOG.md"}
SKIP_PARTS = {".git", ".venv", "node_modules", ".jarvis_runtime", "__pycache__"}


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.name in SPECIAL_NAMES:
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fails when mojibake or UTF-8 BOM is found in tracked text files."
        )
    )
    parser.add_argument("root", nargs="?", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    problems: list[str] = []

    for path in iter_files(root):
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            problems.append(f"{path.relative_to(root)}: utf8-bom")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            problems.append(f"{path.relative_to(root)}: invalid-utf8 ({exc})")
            continue
        if any(token in text for token in SUSPICIOUS_TOKENS):
            problems.append(f"{path.relative_to(root)}: suspicious-token")

    if problems:
        print("Encoding issues found:")
        for problem in problems:
            print(problem)
        return 1

    print("No mojibake or BOM found in scanned text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
