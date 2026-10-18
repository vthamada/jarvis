"""Activity is a bounded projection, not authentication or job execution."""

import copy
import io
import json
from pathlib import Path

import pytest

from apps.jarvis_console import job_activity_cli as activity


def inspection(statuses=("registered", "running", "succeeded", "needs_decision")):
    jobs = []
    for status in statuses:
        jobs.append({
            "event": "fixture_job_state", "status": status, "version": 2,
            "fencing": 1, "attempts": 1, "max_attempts": 3,
            "lease_present": status == "running", "last_outcome": None,
            "evidence_mode": "fixture", "action_authority": False,
            "automatic_execution": False,
        })
    return {
        "schema_version": "jarvis-job-inspection-v1", "read_only": True,
        "authority": "none", "scope_binding": "caller_supplied_not_authentication",
        "source_mode": "quiescent_existing_local_sqlite", "job_count": len(jobs),
        "jobs": jobs,
    }


def build(monkeypatch, product=None, **extra):
    product = inspection() if product is None else product
    calls = []

    def reader(path, **kwargs):
        calls.append((path, kwargs))
        return product

    monkeypatch.setattr(activity, "_inspect", reader)
    args = {
        "actor_ref": "private-actor", "session_ref": "private-session",
        "job_ids": tuple(f"private-job-{i}" for i in range(product["job_count"])),
        "authorized": True,
    }
    args.update(extra)
    return activity.build_job_activity(Path("unused"), **args), calls


def test_derived_counts_are_not_execution_percentage_or_full_ledger(monkeypatch):
    result, calls = build(monkeypatch)
    assert result["schema_version"] == "jarvis-job-activity-v1"
    assert result["selected_job_count"] == 4
    assert result["status_counts"] == {
        "registered": 1, "running": 1, "succeeded": 1, "failed": 0,
        "needs_decision": 1, "cancelled": 0, "expired": 0,
    }
    assert result["progress"] == {
        "basis": "selected_ledger_states_not_execution_percentage",
        "pending_count": 1, "active_count": 1, "awaiting_decision_count": 1,
        "terminal_count": 1,
    }
    assert result["attempts_recorded"] == 4
    assert result["authority"] == "none" and result["operator_authenticated"] is False
    assert result["activity_scope"] == "explicit_selected_jobs_not_full_ledger"
    assert calls[0][1]["include_refs"] is False
    encoded = json.dumps(result)
    for private in ("private", "unused", "worker_id", "references", "percent", "deadline"):
        assert private not in encoded.replace("percentage", "")


def test_all_states_and_evidence_modes(monkeypatch):
    states = ("registered", "running", "succeeded", "failed", "needs_decision",
              "cancelled", "expired")
    product = inspection(states)
    product["jobs"][1].update(event="job_state", evidence_mode="metadata_ledger")
    result, _ = build(monkeypatch, product)
    assert all(value == 1 for value in result["status_counts"].values())
    assert result["progress"]["terminal_count"] == 4
    assert result["evidence_counts"] == {"fixture": 6, "metadata_ledger": 1}


@pytest.mark.parametrize("authorized", [False, None, 1, "true"])
def test_explicit_authorization_required_before_reader(monkeypatch, authorized):
    monkeypatch.setattr(activity, "_inspect", lambda *_a, **_k: pytest.fail("source read"))
    with pytest.raises(activity.JobActivityError, match="^job_activity_refused$"):
        activity.build_job_activity(Path("missing"), actor_ref="actor", session_ref="session",
                                    job_ids=("job",), authorized=authorized)


@pytest.mark.parametrize("change", [
    {"schema_version": "v2"}, {"read_only": 1}, {"authority": "grant"},
    {"scope_binding": "authenticated"}, {"job_count": True}, {"job_count": 5},
    {"jobs": ()}, {"unexpected": "private-marker"},
])
def test_upstream_contract_drift_fails_closed(monkeypatch, change):
    product = inspection()
    product.update(change)
    with pytest.raises(activity.JobActivityError, match="^job_activity_refused$"):
        build(monkeypatch, product, job_ids=("a", "b", "c", "d"))


@pytest.mark.parametrize("change", [
    {"status": "private-marker"}, {"references": {"actor": "private-marker"}},
    {"attempts": True}, {"attempts": -1}, {"attempts": 4}, {"max_attempts": 11},
    {"fencing": 0}, {"version": 2**60}, {"lease_present": 1},
    {"lease_present": True}, {"last_outcome": "private-marker"},
    {"automatic_execution": True}, {"action_authority": 0},
    {"evidence_mode": "metadata_ledger"}, {"event": "private-marker"},
])
def test_untrusted_job_fields_never_become_output(monkeypatch, change):
    product = copy.deepcopy(inspection())
    product["jobs"][0].update(change)
    with pytest.raises(activity.JobActivityError, match="^job_activity_refused$"):
        build(monkeypatch, product)


def test_reader_error_is_sanitized_without_partial_output(monkeypatch, capsys):
    def fail(*_args, **_kwargs):
        raise RuntimeError("password=private-marker/path")

    monkeypatch.setattr(activity, "_inspect", fail)
    assert activity.main(["--authorized", "--job-db", "private/path", "--actor-ref", "actor",
                          "--session-ref", "session", "--job-id", "job"]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err) == {"error_code": "job_activity_refused"}


@pytest.mark.parametrize("argv", [[], ["--private-option=password=private-marker"],
                                  ["--job-db", "password=private-marker"]])
def test_parser_never_echoes_private_argv(argv, capsys):
    assert activity.main(argv) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err) == {"error_code": "job_activity_refused"}


@pytest.mark.parametrize("error_type", [BrokenPipeError, OSError, UnicodeError, ValueError])
@pytest.mark.parametrize("stderr_broken", [False, True])
def test_output_channel_failures_are_contained(monkeypatch, capsys, error_type, stderr_broken):
    class BrokenOutput:
        def write(self, _text):
            raise error_type("password=private-marker/source-path")

    monkeypatch.setattr(activity, "_inspect", lambda *_a, **_k: inspection(("registered",)))
    # Restore streams before pytest/capsys inspects the result, including a
    # failing assertion. The CLI must contain both output-channel failures.
    with monkeypatch.context() as output:
        output.setattr(activity.sys, "stdout", BrokenOutput())
        if stderr_broken:
            output.setattr(activity.sys, "stderr", BrokenOutput())
        result = activity.main([
            "--authorized", "--job-db", "private/path", "--actor-ref", "actor",
            "--session-ref", "session", "--job-id", "job",
        ])
    assert result == 2
    captured = capsys.readouterr()
    assert not captured.out
    if stderr_broken:
        assert not captured.err
    else:
        assert json.loads(captured.err) == {"error_code": "job_activity_refused"}


@pytest.mark.parametrize("error_type", [BrokenPipeError, OSError, UnicodeError, ValueError])
@pytest.mark.parametrize("stderr_broken", [False, True])
def test_flush_only_failures_are_contained(monkeypatch, capsys, error_type, stderr_broken):
    class BrokenFlush:
        def write(self, text):
            return len(text)

        def flush(self):
            raise error_type("password=private-flush-marker/source-path")

    monkeypatch.setattr(activity, "_inspect", lambda *_a, **_k: inspection(("registered",)))
    with monkeypatch.context() as output:
        output.setattr(activity.sys, "stdout", BrokenFlush())
        if stderr_broken:
            output.setattr(activity.sys, "stderr", BrokenFlush())
        result = activity.main([
            "--authorized", "--job-db", "private/path", "--actor-ref", "actor",
            "--session-ref", "session", "--job-id", "job",
        ])
    assert result == 2
    captured = capsys.readouterr()
    assert not captured.out
    if stderr_broken:
        assert not captured.err
    else:
        assert json.loads(captured.err) == {"error_code": "job_activity_refused"}


def test_duck_typed_fake_standard_fileno_cannot_redirect_host(monkeypatch):
    class FakeStandard:
        def fileno(self):
            pytest.fail("fake descriptor inspected")

    monkeypatch.setattr(activity.os, "open", lambda *_a, **_k: pytest.fail("host FD redirected"))
    activity._silence_broken_standard_stream(FakeStandard(), 1)
    activity._silence_broken_standard_stream(FakeStandard(), 2)


def test_real_nonstandard_stream_descriptor_never_redirected(tmp_path, monkeypatch):
    path = tmp_path / "output.txt"
    with path.open("w", encoding="utf-8") as stream:
        assert type(stream) is io.TextIOWrapper and stream.fileno() not in (1, 2)
        monkeypatch.setattr(activity.os, "open",
                            lambda *_a, **_k: pytest.fail("host FD redirected"))
        activity._silence_broken_standard_stream(stream, 1)
        activity._silence_broken_standard_stream(stream, 2)


def test_validation_refusal_never_silences_healthy_stream(monkeypatch, capsys):
    monkeypatch.setattr(activity, "_silence_broken_standard_stream",
                        lambda *_a, **_k: pytest.fail("healthy stream redirected"))
    assert activity.main([]) == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err) == {"error_code": "job_activity_refused"}
