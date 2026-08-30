import pytest

from shared.versioning import parse_canonical_semver


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.0.0", (0, 0, 0)),
        ("1.2.3", (1, 2, 3)),
        ("10.20.30", (10, 20, 30)),
    ],
)
def test_parse_canonical_semver_accepts_ascii_major_minor_patch(
    value: str,
    expected: tuple[int, int, int],
) -> None:
    assert parse_canonical_semver(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "01.0.0",
        "1.01.0",
        "1.0.01",
        "١.2.3",
        "１.2.3",
        "1.2",
        "1.2.3-alpha",
        " 1.2.3",
        "1.2.3 ",
        1,
        None,
    ],
)
def test_parse_canonical_semver_rejects_noncanonical_or_non_ascii_values(
    value: object,
) -> None:
    assert parse_canonical_semver(value) is None
