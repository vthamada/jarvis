from __future__ import annotations

import argparse
from pathlib import Path

SUSPICIOUS_TOKENS = ("Ã", "Â", "�")
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


def read_text(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")
    return text, has_bom


def suspicious_score(text: str) -> int:
    return sum(text.count(token) for token in SUSPICIOUS_TOKENS)


def repair_once(text: str, encoding: str) -> str | None:
    try:
        return text.encode(encoding).decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None


def best_repair(text: str) -> str:
    current = text
    current_score = suspicious_score(current)
    for _ in range(3):
        candidates = [current]
        for encoding in ("latin-1", "cp1252"):
            repaired = repair_once(current, encoding)
            if repaired is not None:
                candidates.append(repaired)
        best = min(candidates, key=suspicious_score)
        best_score = suspicious_score(best)
        if best_score >= current_score:
            break
        current = best
        current_score = best_score
    return current


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def process_file(path: Path) -> tuple[bool, bool, int, int]:
    original, had_bom = read_text(path)
    repaired = best_repair(original)
    normalized = normalize_newlines(repaired)
    changed = normalized != original or had_bom
    if changed:
        path.write_text(normalized, encoding="utf-8", newline="\n")
    return changed, had_bom, suspicious_score(original), suspicious_score(normalized)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Repairs mojibake and normalizes UTF-8/LF text files."
    )
    parser.add_argument("root", nargs="?", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    changed_files: list[Path] = []
    repaired_files = 0
    normalized_bom = 0

    for path in iter_files(root):
        changed, had_bom, before_score, after_score = process_file(path)
        if not changed:
            continue
        changed_files.append(path)
        if after_score < before_score:
            repaired_files += 1
        if had_bom:
            normalized_bom += 1

    print(
        "changed_files="
        f"{len(changed_files)} repaired_files={repaired_files} "
        f"normalized_bom={normalized_bom}"
    )
    for path in changed_files:
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
