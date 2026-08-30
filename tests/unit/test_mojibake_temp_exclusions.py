from pathlib import Path

from tools.check_mojibake import iter_files as iter_checked_files
from tools.fix_mojibake import iter_files as iter_fixable_files


def test_mojibake_tools_ignore_ephemeral_test_roots(tmp_path: Path) -> None:
    tracked = tmp_path / "docs" / "tracked.md"
    tracked.parent.mkdir()
    tracked.write_text("conteudo valido\n", encoding="utf-8")
    for name in (".pytest_case", ".tmp_case", ".audit_case"):
        fixture = tmp_path / name / "docs" / "invalid.txt"
        fixture.parent.mkdir(parents=True)
        fixture.write_bytes(b"invalid-utf8:\xff")

    assert iter_checked_files(tmp_path) == [tracked]
    assert iter_fixable_files(tmp_path) == [tracked]
