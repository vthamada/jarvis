"""Private model environments are not project documentation; canonical docs remain scanned."""

from tools.check_mojibake import iter_files


def test_private_research_excluded_without_excluding_documentation(tmp_path):
    private = tmp_path / ".research" / "voice-lab" / "model" / "README.md"
    private.parent.mkdir(parents=True)
    private.write_bytes(b"\xff private external model metadata")
    canonical = tmp_path / "docs" / "README.md"
    canonical.parent.mkdir()
    canonical.write_text("Canonical documentation", encoding="utf-8")
    assert iter_files(tmp_path) == [canonical]
