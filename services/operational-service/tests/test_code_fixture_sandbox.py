"""Unit and end-to-end evidence for WP-CODE-01, fixture mode only."""

from dataclasses import replace

import pytest
from operational_service.adapters.code_sandbox import (
    CandidatePatch,
    FixtureCase,
    FixtureCodeSandbox,
    FixtureLimits,
    FixtureWorkspace,
    source_digest,
)

BUG = "def add(a, b):\n    return a - b\n"
FIX = "def add(a, b):\n    return a + b\n"
PATH = "src/arithmetic.py"
CASES = (FixtureCase(PATH, "add", (2, 3), 5), FixtureCase(PATH, "add", (-2, 3), 1))


def patch(**kwargs):
    return replace(CandidatePatch(PATH, BUG, FIX, source_digest(BUG)), **kwargs)


def run(source=BUG, patches=(), cases=CASES, **kwargs):
    return FixtureCodeSandbox().run(FixtureWorkspace({PATH: source}), patches, cases, **kwargs)


def test_end_to_end_bug_candidate_interpreted_tests_and_review_diff_preserve_original():
    original = {PATH: BUG}
    workspace = FixtureWorkspace(original)
    sandbox = FixtureCodeSandbox()
    baseline = sandbox.run(workspace, (), CASES)
    assert (baseline.status, baseline.failed, baseline.passed) == ("test_failed", 2, 0)
    candidate = sandbox.run(workspace, (patch(),), CASES)
    assert (candidate.status, candidate.tested, candidate.passed) == ("passed", 2, 2)
    assert candidate.candidate_sha256 != baseline.candidate_sha256
    assert "-    return a - b" in candidate.diff
    assert "+    return a + b" in candidate.diff
    assert candidate.workspace.sources[PATH] == FIX
    assert original == {PATH: BUG} and workspace.sources[PATH] == BUG
    assert candidate.evidence_mode == "fixture"
    assert not candidate.model_generated and not candidate.host_effects
    with pytest.raises(TypeError):
        candidate.workspace.sources[PATH] = BUG


@pytest.mark.parametrize(
    "path",
    [
        "../escape.py",
        "/escape.py",
        "C:/escape.py",
        "C:\\escape.py",
        "//host/share.py",
        "src/../escape.py",
        "src//escape.py",
        "src/./escape.py",
        "src/a.py ",
        "src/a.py.",
        "src/a.py:stream",
        "src/NUL.py",
        "src/COM1.py",
        "src/clock$.py",
        "src/a\x00.py",
        "src/a\n.py",
        "src/a\\b.py",
        "src/a.txt",
        ".git/a.py",
        "src/é.py",
    ],
)
def test_escape_and_cross_platform_alias_paths_fail_closed(path):
    result = run(patches=(patch(path=path),))
    assert (result.status, result.reason, result.workspace) == ("rejected", "invalid_path", None)


@pytest.mark.parametrize(
    "candidate",
    [
        patch(expected_sha256="0" * 64),
        patch(before_text=FIX),
        patch(path="missing.py"),
    ],
)
def test_patch_conflicts_and_missing_files_leave_original_unchanged(candidate):
    result = run(patches=(candidate,))
    assert result.status == "rejected" and result.workspace is None and result.diff == ""


def test_duplicate_patches_and_case_insensitive_workspace_aliases_rejected():
    assert run(patches=(patch(), patch())).reason == "duplicate_patch"
    workspace = FixtureWorkspace({PATH: BUG, PATH.upper().replace(".PY", ".py"): BUG})
    assert FixtureCodeSandbox().run(workspace, (), CASES).reason == "duplicate_path"


@pytest.mark.parametrize(
    "source",
    [
        "import os\ndef add(a,b): return a+b",
        "def add(a,b): return __import__('os')",
        "def add(a,b): return a.real",
        "def add(a,b): return a ** b",
        "def add(a,b): return [a,b]",
        "def add(a,b): return 'secret'",
        "def add(a,b): return True",
        "def add(a,b): return x",
        "def add(a,b):\n while True: pass",
        "class C: pass",
        "@decorator\ndef add(a,b): return a+b",
        "def add(a,b=1): return a+b",
        "def add(a,b):\n a = b\n return a",
        "def add(a,b): return lambda: a",
        "def add(a,b): return a if b else 0",
        "def add(a,b): yield a",
        "async def add(a,b): return a+b",
        "def add(a: int,b): return a+b",
        "def add(*args): return 1",
        "def add(a,b): return a+b\ndef add(a,b): return a-b",
        "def add(a,a): return a",
        "def add(a,b):",
        "",
    ],
)
def test_unsupported_python_never_executes_and_never_passes(source):
    result = run(source=source)
    assert result.status == "rejected" and result.tested == 0 and result.workspace is None


def test_untested_source_is_also_checked():
    workspace = FixtureWorkspace({PATH: BUG, "untested.py": "import os"})
    assert FixtureCodeSandbox().run(workspace, (), CASES).reason == "unsupported_syntax"


@pytest.mark.parametrize(
    "expression,args,expected",
    [
        ("a + b", (7, 2), 9),
        ("a - b", (7, 2), 5),
        ("a * b", (7, 2), 14),
        ("a // b", (7, 2), 3),
        ("a % b", (7, 2), 1),
        ("-a + +b + 2", (7, 2), -3),
    ],
)
def test_supported_arithmetic_evaluates_without_python_execution(expression, args, expected):
    source = f"def calculate(a,b): return {expression}"
    case = FixtureCase(PATH, "calculate", args, expected)
    assert run(source=source, cases=(case,)).status == "passed"


def test_integer_overflow_divide_by_zero_and_noninteger_inputs_rejected():
    assert run(cases=(replace(CASES[0], arguments=(True, 3)),)).reason == "integer_limit"
    source = "def add(a,b): return a*b"
    overflow_case = replace(CASES[0], arguments=(2**63, 3))
    assert run(source=source, cases=(overflow_case,)).reason == "integer_limit"
    source = "def add(a,b): return a//b"
    zero_case = replace(CASES[0], arguments=(2, 0))
    assert run(source=source, cases=(zero_case,)).reason == "arithmetic_error"


@pytest.mark.parametrize(
    "changes,source,cases,reason",
    [
        ({"max_source_chars": 8}, BUG, CASES, "source_limit"),
        ({"max_total_chars": 8}, BUG, CASES, "source_limit"),
        ({"max_cases": 1}, BUG, CASES, "case_or_patch_limit"),
        ({"max_ast_nodes": 2}, BUG, CASES, "ast_limit"),
        ({"max_ast_depth": 2}, BUG, CASES, "ast_limit"),
        ({"max_arguments": 1}, BUG, CASES, "unsupported_syntax"),
    ],
)
def test_work_bounds(changes, source, cases, reason):
    sandbox = FixtureCodeSandbox(FixtureLimits(**changes))
    assert sandbox.run(FixtureWorkspace({PATH: source}), (), cases).reason == reason


def test_cancel_and_deadline_before_and_during_evaluation_return_no_candidate():
    assert run(cancelled=lambda: True).status == "cancelled"
    clock_values = iter((0, 2))
    assert run(clock=lambda: next(clock_values)).status == "timed_out"
    ticks = iter(i / 100 for i in range(1000))
    result = FixtureCodeSandbox(FixtureLimits(timeout_seconds=0.15)).run(
        FixtureWorkspace({PATH: BUG}),
        (patch(),),
        CASES,
        clock=lambda: next(ticks),
    )
    assert result.status == "timed_out" and result.workspace is None
    calls = 0

    def cancel_later():
        nonlocal calls
        calls += 1
        return calls > 12

    assert run(patches=(patch(),), cancelled=cancel_later).status == "cancelled"


def test_workspace_copies_caller_and_no_tests_cannot_be_a_success():
    original = {PATH: BUG}
    workspace = FixtureWorkspace(original)
    original[PATH] = FIX
    assert workspace.sources[PATH] == BUG
    assert run(cases=()).status == "rejected"


def test_content_free_telemetry_and_repr_do_not_expose_source_or_case():
    result = run(patches=(patch(),))
    projection = str(result.telemetry()) + repr(result) + repr(patch()) + repr(CASES[0])
    assert "return a" not in projection and PATH not in projection and "arguments" not in projection
    assert set(result.telemetry()) == {
        "status",
        "reason",
        "tested",
        "passed",
        "failed",
        "candidate_sha256",
        "evidence_mode",
        "model_generated",
        "host_effects",
    }


def test_malformed_contracts_and_invalid_unicode_fail_closed():
    assert run(patches=("invalid",)).reason == "invalid_patch"
    assert run(cases=("invalid",)).reason == "invalid_case"
    assert run(source="\ud800").reason == "invalid_source"
    assert run(patches=(patch(after_text="\ud800"),)).reason == "invalid_source"
    assert run(cases=(replace(CASES[0], function="other"),)).reason == "unknown_function"
    assert run(cases=(replace(CASES[0], arguments=(2,)),)).reason == "invalid_arguments"


@pytest.mark.parametrize(
    "changes",
    [
        {"max_ast_nodes": 0},
        {"max_integer_bits": 129},
        {"timeout_seconds": float("nan")},
        {"max_cases": True},
    ],
)
def test_limits_cannot_disable_hard_ceiling(changes):
    with pytest.raises(ValueError, match="invalid_fixture_limits"):
        FixtureLimits(**changes)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "secret"])
def test_invalid_clock_fails_closed(value):
    assert run(clock=lambda: value).reason == "invalid_clock"


def test_clock_regression_fails_closed():
    values = iter((2, 1))
    assert run(clock=lambda: next(values)).reason == "invalid_clock"


def test_control_callback_errors_are_sanitized():
    def broken():
        raise RuntimeError("private token")

    for result in (run(clock=broken), run(cancelled=broken), run(cancelled=lambda: "private")):
        assert result.status == "rejected" and result.reason == "control_error"
        assert "private" not in str(result.telemetry())
        assert result.workspace is None


def test_file_and_patch_limits_and_collection_types_fail_closed():
    sandbox = FixtureCodeSandbox(FixtureLimits(max_files=1, max_patches=1))
    workspace = FixtureWorkspace({PATH: BUG, "other.py": FIX})
    assert sandbox.run(workspace, (), CASES).reason == "file_limit"
    assert sandbox.run(FixtureWorkspace({PATH: BUG}), (patch(), patch()), CASES).reason == (
        "case_or_patch_limit"
    )
    assert run(patches=None).reason == "invalid_collection"
    assert run(cases=None).reason == "invalid_collection"
    assert sandbox.run(None, (), CASES).reason == "invalid_workspace"
    with pytest.raises(ValueError, match="invalid_fixture_limits"):
        FixtureCodeSandbox({})


def test_rejected_second_patch_does_not_publish_partial_workspace_or_mutate_first_file():
    workspace = FixtureWorkspace({PATH: BUG, "other.py": FIX})
    second = CandidatePatch("other.py", FIX, BUG, "incorrect")
    result = FixtureCodeSandbox().run(workspace, (patch(), second), CASES)
    assert result.reason == "patch_conflict" and result.workspace is None and result.diff == ""
    assert workspace.sources[PATH] == BUG and workspace.sources["other.py"] == FIX
