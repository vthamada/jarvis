import stat
from os import link
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.jarvis_console import recall_cli
from apps.jarvis_console.runtime import ConsoleCommandError


def test_windows_reparse_ancestor_is_refused_without_resolving(monkeypatch, tmp_path):
    source = tmp_path / "private.sqlite3"
    calls = []

    def lstat(path):
        calls.append(path)
        return SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=(
            0x400 if path == tmp_path else 0
        ))

    monkeypatch.setattr(Path, "lstat", lstat)
    with pytest.raises(ConsoleCommandError, match="Memory recall refused"):
        recall_cli._database_path(source)
    assert calls == [source, tmp_path]


def test_safe_text_escapes_terminal_and_bidi_controls():
    assert recall_cli._safe_text("a\x00\x1b\n\t\u202eé") == "a\\u0000\\u001b\\u000a\\u0009\\u202eé"


def test_safe_text_escapes_unicode_line_and_paragraph_separators():
    assert recall_cli._safe_text("first\u2028second\u2029third") == (
        "first\\u2028second\\u2029third"
    )


def test_database_hardlink_alias_is_refused(tmp_path):
    original = tmp_path / "original.sqlite3"
    original.write_bytes(b"x" * 100)
    alias = tmp_path / "alias.sqlite3"
    try:
        link(original, alias)
    except OSError:
        pytest.skip("hardlink capability unavailable")
    before = original.read_bytes()
    for path in (original, alias):
        with pytest.raises(ConsoleCommandError, match="Memory recall refused"):
            recall_cli._database_path(path)
    assert original.read_bytes() == before
    assert alias.read_bytes() == before
