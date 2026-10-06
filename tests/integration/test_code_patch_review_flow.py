"""Offline candidate -> exact preview -> independent arithmetic fixture assessment."""

from dataclasses import replace

from operational_service.adapters.code_sandbox import (
    CandidatePatch,
    FixtureCase,
    FixtureCodeSandbox,
    FixtureWorkspace,
)
from operational_service.adapters.code_sandbox.patch_review import (
    FileEdits,
    PatchProposal,
    PatchReviewer,
    TextEdit,
    text_sha256,
)

BEFORE = "def add(a, b):\n    return a - b\n"


def candidate_preview(replacement):
    reviewer = PatchReviewer(("src/math.py",))
    original = {"src/math.py": BEFORE}
    snapshot = reviewer.snapshot(original)
    offset = BEFORE.index("-")
    proposal = PatchProposal(
        snapshot.sha256,
        (
            FileEdits(
                "src/math.py",
                text_sha256(BEFORE),
                (TextEdit(offset, offset + 1, "-", replacement),),
            ),
        ),
    )
    return reviewer, snapshot, reviewer.preview(snapshot, proposal), original


def assess_fixture(preview):
    (candidate,) = preview.candidate.files
    # Expectations are independently fixed by the fixture owner, never supplied by proposal.
    cases = (
        FixtureCase("src/math.py", "add", (2, 3), 5),
        FixtureCase("src/math.py", "add", (-2, 4), 2),
        FixtureCase("src/math.py", "add", (0, 8), 8),
    )
    return FixtureCodeSandbox().run(
        FixtureWorkspace({"src/math.py": BEFORE}),
        (CandidatePatch("src/math.py", BEFORE, candidate.text, text_sha256(BEFORE)),),
        cases,
    )


def test_candidate_review_and_independent_fixture_expectations_are_distinct(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reviewer, snapshot, preview, original = candidate_preview("+")
    verified = reviewer.verify(preview, snapshot, expected_proposal_sha256=preview.proposal_sha256)
    assert verified.status == "reviewable"
    result = assess_fixture(verified)
    assert (result.status, result.passed, result.failed) == ("passed", 3, 0)
    assert result.evidence_mode == "fixture"
    assert result.host_effects is False
    assert verified.tests_executed is False
    assert verified.authority_granted is False
    assert original == {"src/math.py": BEFORE}
    assert list(tmp_path.iterdir()) == []


def test_reviewable_patch_can_be_wrong_against_independent_tests():
    _, _, preview, _ = candidate_preview("*")
    assert preview.status == "reviewable"
    result = assess_fixture(preview)
    assert result.status == "test_failed"
    assert result.failed == 3
    assert preview.tests_executed is False
    assert preview.authority_granted is False


def test_stale_user_edit_denies_review_before_any_assessment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reviewer, _, preview, original = candidate_preview("+")
    current = reviewer.snapshot({"src/math.py": BEFORE + "# human changed file\n"})
    denied = reviewer.verify(preview, current, expected_proposal_sha256=preview.proposal_sha256)
    assert (denied.status, denied.reason) == ("rejected", "snapshot_conflict")
    assert denied.candidate is None
    assert denied.diff == ""
    assert original["src/math.py"] == BEFORE
    assert list(tmp_path.iterdir()) == []


def test_tampered_candidate_never_becomes_a_reviewed_candidate():
    reviewer, snapshot, preview, _ = candidate_preview("+")
    substituted = reviewer.snapshot({"src/math.py": "import os\n"})
    denied = reviewer.verify(
        replace(preview, candidate=substituted),
        snapshot,
        expected_proposal_sha256=preview.proposal_sha256,
    )
    assert (denied.status, denied.reason) == ("rejected", "preview_tampered")
    assert denied.authority_granted is False
