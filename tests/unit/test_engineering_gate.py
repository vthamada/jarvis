import os
import xml.etree.ElementTree as ET
from argparse import Namespace
from pathlib import Path
from subprocess import run
from sys import executable

import pytest

from tools import engineering_gate
from tools.engineering_gate import GateStep, build_gate_steps, run_step


def test_engineering_gate_quick_mode() -> None:
    steps = build_gate_steps(mode="quick", include_controlled=False)

    assert [step.label for step in steps] == [
        "mojibake check",
        "document guardrails",
        "ruff",
    ]


def test_engineering_gate_standard_mode() -> None:
    steps = build_gate_steps(mode="standard", include_controlled=False)

    assert [step.label for step in steps] == [
        "mojibake check",
        "document guardrails",
        "ruff",
        "pytest",
    ]
    assert "--basetemp" in steps[-1].command


def test_engineering_gate_release_mode_with_controlled() -> None:
    steps = build_gate_steps(mode="release", include_controlled=True)

    assert [step.label for step in steps] == [
        "mojibake check",
        "document guardrails",
        "ruff",
        "pytest",
        "axis artifact verification",
        "release signal baseline verification",
        "active cut baseline verification",
        "current cut closure verification",
        "baseline validation development",
        "baseline validation controlled",
    ]
    assert "--basetemp" in steps[3].command
    assert steps[7].command[-1] == "--check"


def test_release_active_cut_uses_source_module_without_editable_install() -> None:
    steps = build_gate_steps(mode="release", include_controlled=False)
    assert steps[6].command[1:] == ["-m", "tools.verify_active_cut_baseline"]
    # A fresh process without site initialization cannot rely on editable installs
    # or pytest's sys.path setup. Help must load the public CLI without writing.
    result = run(
        [executable, "-E", "-S", "-m", "tools.verify_active_cut_baseline", "--help"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--output-dir" in result.stdout


def test_gate_uses_fresh_system_temp_without_creating_it() -> None:
    first_steps = build_gate_steps(mode="standard", include_controlled=False)
    second_steps = build_gate_steps(mode="standard", include_controlled=False)
    first_command = first_steps[-1].command
    second_command = second_steps[-1].command
    first = Path(first_command[first_command.index("--basetemp") + 1])
    second = Path(second_command[second_command.index("--basetemp") + 1])

    assert first.name == second.name == "pytest"
    system_temp = Path(engineering_gate.gettempdir()).resolve()
    assert first.parent.parent == second.parent.parent == system_temp
    assert not first.parent.resolve().is_relative_to(engineering_gate.ROOT.resolve())
    assert first.parent.name.startswith("jarvis-engineering-gate-")
    assert first != second
    assert not first.parent.exists()
    assert not second.parent.exists()


def test_gate_uses_explicit_run_temp_for_standard_and_release(tmp_path) -> None:
    run_temp = tmp_path / "run"
    for mode in ("standard", "release"):
        steps = build_gate_steps(mode=mode, include_controlled=False, temp_root=run_temp)
        step = next(step for step in steps if step.label == "pytest")
        assert step.command[1:] == [
            "-m", "pytest", "-q", "--basetemp", str(run_temp / "pytest"),
            "--junitxml", str(run_temp / "pytest-results.xml"),
        ]
    assert not run_temp.exists()


def test_gate_child_environment_is_scoped_and_preserves_other_values(tmp_path, monkeypatch) -> None:
    captured = {}
    monkeypatch.setenv("TEMP", "unavailable-system-temp")
    monkeypatch.setenv("TMP", "another-system-temp")
    monkeypatch.setenv("TMPDIR", "unix-system-temp")
    monkeypatch.setenv("JARVIS_GATE_TEST_SENTINEL", "preserved")
    original = dict(os.environ)

    def fake_run(command, *, check, env):
        captured.update(command=command, check=check, env=env)
        return Namespace(returncode=0)

    monkeypatch.setattr(engineering_gate, "run", fake_run)
    step = GateStep("probe", [executable, "-c", "pass"])
    run_step(step, temp_root=tmp_path)

    assert captured["command"] == step.command
    assert captured["check"] is False
    assert captured["env"]["PATH"] == original["PATH"]
    assert captured["env"]["JARVIS_GATE_TEST_SENTINEL"] == "preserved"
    assert all(captured["env"][name] == str(tmp_path) for name in ("TEMP", "TMP", "TMPDIR"))
    assert dict(os.environ) == original


@pytest.mark.parametrize("mode", ["standard", "release"])
def test_gate_rejects_inherited_pytest_selection_before_running(
    mode, tmp_path, monkeypatch,
) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k nonexistent_gate_test")
    monkeypatch.setattr(engineering_gate, "ROOT", tmp_path)
    monkeypatch.setattr(
        engineering_gate, "parse_args", lambda: Namespace(mode=mode, include_controlled=False)
    )

    def unexpected_run(*args, **kwargs):
        pytest.fail("no gate step may execute with inherited pytest selection")

    monkeypatch.setattr(engineering_gate, "run", unexpected_run)
    with pytest.raises(RuntimeError, match="PYTEST_ADDOPTS"):
        engineering_gate.main()
    assert list(tmp_path.iterdir()) == []


def test_quick_gate_does_not_reject_pytest_options_or_allocate_temp(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k example")
    monkeypatch.setattr(engineering_gate, "ROOT", tmp_path)
    monkeypatch.setattr(engineering_gate, "gettempdir", lambda: pytest.fail("unused system TEMP"))
    monkeypatch.setattr(
        engineering_gate, "parse_args", lambda: Namespace(mode="quick", include_controlled=False)
    )
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Namespace(returncode=0)

    monkeypatch.setattr(engineering_gate, "run", fake_run)
    engineering_gate.main()

    assert len(calls) == 3
    assert list(tmp_path.iterdir()) == []


def test_gate_main_allocates_fresh_scoped_temp_and_shares_it(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.setattr(engineering_gate, "ROOT", tmp_path / "repo")
    monkeypatch.setattr(engineering_gate, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(
        engineering_gate, "parse_args", lambda: Namespace(mode="standard", include_controlled=False)
    )
    calls = []

    def fake_run_step(step, *, temp_root=None):
        calls.append((step, temp_root))

    monkeypatch.setattr(engineering_gate, "run_step", fake_run_step)
    engineering_gate.main()
    first_temp = calls[0][1]
    assert first_temp.is_dir()
    assert first_temp.parent == tmp_path
    assert first_temp.name.startswith("jarvis-engineering-gate-")
    assert all(root == first_temp for _, root in calls)
    pytest_command = calls[-1][0].command
    assert pytest_command[pytest_command.index("--basetemp") + 1] == str(first_temp / "pytest")
    engineering_gate.main()
    assert calls[4][1] != first_temp
    assert first_temp.is_dir()


def test_gate_temp_path_rejects_existing_target_without_deleting_it(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.setattr(engineering_gate, "ROOT", tmp_path / "repo")
    monkeypatch.setattr(engineering_gate, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(engineering_gate, "uuid4", lambda: Namespace(hex="collision"))
    monkeypatch.setattr(
        engineering_gate, "parse_args", lambda: Namespace(mode="standard", include_controlled=False)
    )

    def unexpected_step(*args, **kwargs):
        pytest.fail("existing run directory must be rejected before any step")

    monkeypatch.setattr(engineering_gate, "run_step", unexpected_step)
    target = tmp_path / "jarvis-engineering-gate-collision"
    target.mkdir()
    sentinel = target / "user-data.txt"
    sentinel.write_text("do not delete", encoding="utf-8")

    with pytest.raises(FileExistsError):
        engineering_gate.main()
    assert sentinel.read_text(encoding="utf-8") == "do not delete"


def test_real_child_tempfile_uses_gate_workspace_temp(tmp_path) -> None:
    # The temporary environment is exercised in a fresh interpreter, rather than
    # the test interpreter whose tempfile.gettempdir() may already be cached.
    program = (
        "from pathlib import Path; from tempfile import TemporaryDirectory, gettempdir; "
        "import sys; expected=Path(sys.argv[1]).resolve(); "
        "assert Path(gettempdir()).resolve() == expected; "
        "scratch=TemporaryDirectory(); "
        "assert Path(scratch.name).resolve().parent == expected; "
        "scratch.cleanup()"
    )
    run_step(GateStep("tempfile probe", [executable, "-c", program, str(tmp_path)]),
             temp_root=tmp_path)


def test_real_child_pytest_reproduces_console_temp_regression(tmp_path) -> None:
    # This is the first test whose setup failed under the sandbox system TEMP.
    # Invoke the unchanged public test in a fresh process through the gate seam.
    # It exercises tmp_path and CLI validation, not network/model execution.
    basetemp = tmp_path / "pytest"
    assert not basetemp.exists()
    command = [
        executable, "-m", "pytest", "-q", "-o", "addopts=-p no:cacheprovider",
        "--basetemp", str(basetemp),
        "apps/jarvis_console/tests/test_console.py::"
        "test_console_technology_radar_rejects_json_for_mutating_intake",
    ]
    run_step(GateStep("pytest", command), temp_root=tmp_path)


def test_gate_failed_step_still_fails(monkeypatch) -> None:
    monkeypatch.setattr(engineering_gate, "run", lambda *args, **kwargs: Namespace(returncode=7))
    with pytest.raises(RuntimeError, match="'probe'.*7"):
        run_step(GateStep("probe", [executable, "-c", "pass"]))


@pytest.mark.parametrize("mode", ["standard", "release"])
def test_gate_junit_report_is_inside_run_root_and_outside_pytest_cleanup(tmp_path, mode) -> None:
    run_temp = tmp_path / "run"
    steps = build_gate_steps(mode=mode, include_controlled=False, temp_root=run_temp)
    step = next(step for step in steps if step.label == "pytest")
    report = Path(step.command[step.command.index("--junitxml") + 1])
    basetemp = Path(step.command[step.command.index("--basetemp") + 1])

    assert report == run_temp / "pytest-results.xml"
    assert report.parent == basetemp.parent == run_temp
    assert not report.is_relative_to(basetemp)
    assert not run_temp.exists()


def test_gate_junit_report_retains_exact_failure_counts_after_child_failure(tmp_path) -> None:
    run_temp = tmp_path / "run"
    run_temp.mkdir()
    sample = tmp_path / "test_expected_results.py"
    sample.write_text(
        "def test_expected_pass():\n    assert True\n\n"
        "def test_expected_failure():\n    assert False\n",
        encoding="utf-8",
    )
    step = next(
        step for step in build_gate_steps(
            mode="standard", include_controlled=False, temp_root=run_temp,
        ) if step.label == "pytest"
    )
    report = Path(step.command[step.command.index("--junitxml") + 1])
    command = [*step.command, str(sample), "-o", "addopts=-p no:cacheprovider"]
    with pytest.raises(RuntimeError, match="'pytest'.*1"):
        run_step(GateStep("pytest", command), temp_root=run_temp)
    suites = ET.parse(report).getroot().findall("testsuite")
    assert sum(int(suite.attrib["tests"]) for suite in suites) == 2
    assert sum(int(suite.attrib["failures"]) for suite in suites) == 1
    assert sum(int(suite.attrib["errors"]) for suite in suites) == 0
    assert sum(int(suite.attrib["skipped"]) for suite in suites) == 0


def test_default_gate_temp_is_outside_repository() -> None:
    step = next(
        step for step in build_gate_steps(mode="standard", include_controlled=False)
        if step.label == "pytest"
    )
    basetemp = Path(step.command[step.command.index("--basetemp") + 1])
    assert not basetemp.resolve().is_relative_to(engineering_gate.ROOT.resolve())


def test_real_gate_temp_allows_unchanged_private_canonical_mission_integration(tmp_path) -> None:
    # Exercise the same validated explicit-parent path used by --temp-root.
    # The external test basetemp is intentionally not inside the checkout.
    selected_run_temp = engineering_gate._new_temp_root(tmp_path)
    step = next(
        step for step in build_gate_steps(
            mode="standard", include_controlled=False, temp_root=selected_run_temp,
        )
        if step.label == "pytest"
    )
    basetemp = Path(step.command[step.command.index("--basetemp") + 1])
    run_temp = basetemp.parent
    run_temp.mkdir(exist_ok=False)
    command = [
        *step.command,
        "tests/integration/test_canonical_mission_port.py::"
        "test_native_output_is_exact_stored_final_not_rewritten_as_json",
        "-o", "addopts=-p no:cacheprovider",
    ]
    run_step(GateStep("pytest", command), temp_root=run_temp)
    assert not basetemp.resolve().is_relative_to(engineering_gate.ROOT.resolve())
    report = Path(step.command[step.command.index("--junitxml") + 1])
    suites = ET.parse(report).getroot().findall("testsuite")
    assert sum(int(suite.attrib["tests"]) for suite in suites) == 1
    assert sum(int(suite.attrib["failures"]) for suite in suites) == 0
    assert sum(int(suite.attrib["errors"]) for suite in suites) == 0


@pytest.mark.parametrize("selection", ["relative", "missing", "file", "repository", "inside"])
def test_gate_rejects_invalid_selected_temp_parent_before_any_step(
    tmp_path, monkeypatch, selection,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    inside = repository / "nested"
    inside.mkdir()
    regular = tmp_path / "file.txt"
    regular.write_text("not a directory", encoding="utf-8")
    choices = {"relative": Path("relative"), "missing": tmp_path / "missing",
               "file": regular, "repository": repository, "inside": inside}
    monkeypatch.setattr(engineering_gate, "ROOT", repository)
    monkeypatch.setattr(
        engineering_gate, "parse_args",
        lambda: Namespace(mode="standard", include_controlled=False,
                          temp_root=choices[selection]),
    )

    def unexpected_step(*args, **kwargs):
        pytest.fail("invalid temporary parent must fail before checks")

    monkeypatch.setattr(engineering_gate, "run_step", unexpected_step)
    with pytest.raises(ValueError, match="outside the repository"):
        engineering_gate.main()
    assert list(inside.iterdir()) == []
    assert sorted(path.name for path in tmp_path.iterdir()) == ["file.txt", "repo"]


def test_gate_selected_private_parent_overrides_unusable_system_temp(tmp_path, monkeypatch) -> None:
    repository = tmp_path / "repo"
    private_parent = tmp_path / "private"
    repository.mkdir()
    private_parent.mkdir()
    monkeypatch.delenv("PYTEST_ADDOPTS", raising=False)
    monkeypatch.setattr(engineering_gate, "ROOT", repository)
    monkeypatch.setattr(
        engineering_gate, "parse_args",
        lambda: Namespace(mode="standard", include_controlled=False, temp_root=private_parent),
    )
    monkeypatch.setattr(engineering_gate, "gettempdir", lambda: pytest.fail("unusable system TEMP"))
    calls = []
    monkeypatch.setattr(
        engineering_gate, "run_step", lambda step, *, temp_root: calls.append((step, temp_root)),
    )
    engineering_gate.main()
    assert len(calls) == 4
    selected = calls[0][1]
    assert selected.parent == private_parent
    assert selected.is_dir() and not selected.is_relative_to(repository)
    assert all(root == selected for _, root in calls)
    assert list(repository.iterdir()) == []


def test_gate_cli_accepts_explicit_temp_parent(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("sys.argv", ["engineering_gate.py", "--temp-root", str(tmp_path)])
    args = engineering_gate.parse_args()
    assert args.mode == "standard" and args.temp_root == tmp_path


def test_default_gate_rejects_system_temp_inside_repository(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(engineering_gate, "ROOT", tmp_path)
    monkeypatch.setattr(engineering_gate, "gettempdir", lambda: str(tmp_path))
    with pytest.raises(ValueError, match="outside the repository"):
        build_gate_steps(mode="standard", include_controlled=False)
    assert list(tmp_path.iterdir()) == []


def test_real_gate_temp_preserves_unchanged_encoding_scanner_regressions(tmp_path) -> None:
    # Scanner exclusions inspect every absolute ancestor, so the gate's own
    # private temp name must not look like an excluded .tmp_ fixture directory.
    selected_run_temp = engineering_gate._new_temp_root(tmp_path)
    step = next(
        step for step in build_gate_steps(
            mode="standard", include_controlled=False, temp_root=selected_run_temp,
        ) if step.label == "pytest"
    )
    selected_run_temp.mkdir(exist_ok=False)
    command = [
        *step.command,
        "tests/unit/test_mojibake_private_runtime.py::"
        "test_private_research_excluded_without_excluding_documentation",
        "tests/unit/test_mojibake_temp_exclusions.py::"
        "test_mojibake_tools_ignore_ephemeral_test_roots",
        "-o", "addopts=-p no:cacheprovider",
    ]
    run_step(GateStep("pytest", command), temp_root=selected_run_temp)
    report = Path(step.command[step.command.index("--junitxml") + 1])
    suites = ET.parse(report).getroot().findall("testsuite")
    assert sum(int(suite.attrib["tests"]) for suite in suites) == 2
    assert sum(int(suite.attrib["failures"]) for suite in suites) == 0
    assert sum(int(suite.attrib["errors"]) for suite in suites) == 0
