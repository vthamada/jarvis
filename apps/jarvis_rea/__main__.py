"""Explicit local-file import of static REA evidence; no REA execution or network."""

from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path, PureWindowsPath

from apps.jarvis_console.review_input import MAX_OUTPUT_BYTES
from apps.jarvis_rea.bridge import _validate_options, review_evidence

MAX_EVIDENCE_BYTES = 2 * 1024 * 1024
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _invalid():
    raise ValueError("invalid_rea_evidence_input")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _linked(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_POINT
    )


def _read_evidence(filename):
    # Explicitly local regular files only, not pipes, device paths or UNC shares.
    if PureWindowsPath(filename).drive.startswith("\\\\"):
        _invalid()
    selected = Path(filename).absolute()
    if selected.is_reserved():
        _invalid()
    for component in (*reversed(selected.parents), selected):
        if _linked(component.lstat()):
            _invalid()
    before = selected.lstat()
    if not stat.S_ISREG(before.st_mode) or not 1 <= before.st_size <= MAX_EVIDENCE_BYTES:
        _invalid()
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(selected, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (
            _linked(opened)
            or not stat.S_ISREG(opened.st_mode)
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
            or not 1 <= opened.st_size <= MAX_EVIDENCE_BYTES
        ):
            _invalid()
        raw = stream.read(MAX_EVIDENCE_BYTES + 1)
    if not 1 <= len(raw) <= MAX_EVIDENCE_BYTES:
        _invalid()
    document = json.loads(
        raw.decode("utf-8", errors="strict"),
        object_pairs_hook=_unique_object,
        parse_constant=lambda _: _invalid(),
    )
    if type(document) is not dict:
        _invalid()
    return document


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        _invalid()


def main(argv=None):
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--confirm-reviewed-selection", action="store_true", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--include-content", action="store_true")
    try:
        args = parser.parse_args(argv)
        _validate_options(
            args.authorized, args.confirm_reviewed_selection, args.session_id,
            args.include_content, None,
        )
        document = _read_evidence(args.evidence)
        result = review_evidence(
            document, authorized=args.authorized, confirmed=args.confirm_reviewed_selection,
            session_id=args.session_id, include_content=args.include_content,
        )
        encoded = json.dumps(result, ensure_ascii=True, allow_nan=False, sort_keys=True)
        if len(encoded.encode("ascii")) > MAX_OUTPUT_BYTES:
            _invalid()
        print(encoded)
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"cancelled","authority":"none"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"invalid_rea_evidence_input","authority":"none"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
