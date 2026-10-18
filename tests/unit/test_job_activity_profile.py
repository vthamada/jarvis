"""The host activity binding remains inert, fixed and metadata-only."""

import copy
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from apps.jarvis_api import job_activity_profile as activity


def product():
    return {
        "schema_version": "jarvis-job-activity-v1", "read_only": True,
        "authority": "none", "operator_authenticated": False,
        "scope_binding": "caller_supplied_not_authentication",
        "source_mode": "quiescent_existing_local_sqlite",
        "activity_scope": "explicit_selected_jobs_not_full_ledger",
        "selected_job_count": 2,
        "status_counts": {"registered": 1, "running": 1, "succeeded": 0,
                          "failed": 0, "needs_decision": 0, "cancelled": 0, "expired": 0},
        "evidence_counts": {"fixture": 1, "metadata_ledger": 1},
        "attempts_recorded": 1,
        "progress": {"basis": "selected_ledger_states_not_execution_percentage",
                     "pending_count": 1, "active_count": 1,
                     "awaiting_decision_count": 0, "terminal_count": 0},
    }


def config(tmp_path, **change):
    args = dict(authorized=True, database_path=tmp_path / "private-ledger.db",
                actor_ref="private-actor", session_ref="private-session",
                job_ids=("private-a", "private-b"))
    args.update(change)
    return args


def test_constructor_inert_and_repr_redacted(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "open", lambda *_a, **_k: pytest.fail("source open"))
    monkeypatch.setattr(Path, "stat", lambda *_a, **_k: pytest.fail("source stat"))
    monkeypatch.setattr(activity, "build_job_activity",
                        lambda *_a, **_k: pytest.fail("reader called"))
    profile = activity.JobActivityProfile(**config(tmp_path))
    assert "private" not in repr(profile)
    assert "authority='none'" in repr(profile)
    with pytest.raises(FrozenInstanceError):
        profile.authorized = False


@pytest.mark.parametrize("change", [
    {"authorized": False}, {"authorized": 1}, {"authorized": None},
    {"database_path": Path("relative.db")}, {"database_path": "private.db"},
    {"actor_ref": ""}, {"actor_ref": "password=private"}, {"session_ref": "a\nb"},
    {"job_ids": []}, {"job_ids": ()}, {"job_ids": ("a", "a")},
    {"job_ids": ("a", "private secret")}, {"job_ids": tuple(f"j{i}" for i in range(33))},
    {"actor_ref": "a" * 129}, {"session_ref": 1},
])
def test_invalid_config_refuses_before_io(tmp_path, monkeypatch, change):
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: pytest.fail("read"))
    with pytest.raises(ValueError, match="^invalid_job_activity_profile$"):
        activity.JobActivityProfile(**config(tmp_path, **change))


def test_default_not_authorized(tmp_path):
    args = config(tmp_path)
    args.pop("authorized")
    with pytest.raises(ValueError, match="^invalid_job_activity_profile$"):
        activity.JobActivityProfile(**args)


def test_scope_exact_and_response_detached(tmp_path, monkeypatch):
    source, calls = product(), []
    def reader(path, **kwargs):
        calls.append((path, kwargs))
        return source
    monkeypatch.setattr(activity, "build_job_activity", reader)
    profile = activity.JobActivityProfile(**config(tmp_path))
    result = profile.read()
    assert result == source and result is not source
    result["status_counts"]["registered"] = 0
    assert source["status_counts"]["registered"] == 1
    assert calls == [(tmp_path / "private-ledger.db", {
        "authorized": True, "actor_ref": "private-actor", "session_ref": "private-session",
        "job_ids": ("private-a", "private-b"),
    })]
    assert len(json.dumps(source).encode()) <= 4096
    assert "private" not in json.dumps(source)


@pytest.mark.parametrize("field,value", [
    ("authority", "grant"), ("read_only", 1), ("operator_authenticated", True),
    ("selected_job_count", True), ("selected_job_count", 3),
    ("schema_version", "v2"), ("source_mode", "live"),
    ("scope_binding", "authenticated"), ("activity_scope", "full_ledger"),
    ("attempts_recorded", -1), ("attempts_recorded", True),
    ("attempts_recorded", 21), ("attempts_recorded", 0),
    ("references", "password=private"), ("percentage", 50),
])
def test_forged_top_level_refused(tmp_path, monkeypatch, field, value):
    source = product()
    source[field] = value
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: source)
    with pytest.raises(activity.JobActivityUnavailable, match="^job_activity_unavailable$"):
        activity.JobActivityProfile(**config(tmp_path)).read()


@pytest.mark.parametrize("container,field,value", [
    ("status_counts", "running", True), ("status_counts", "running", -1),
    ("status_counts", "registered", 2), ("status_counts", "unknown", 0),
    ("evidence_counts", "fixture", 2), ("evidence_counts", "fixture", 1.0),
    ("evidence_counts", "network", 0), ("progress", "terminal_count", 1),
    ("progress", "active_count", 0), ("progress", "pending_count", False),
    ("progress", "awaiting_decision_count", 1), ("progress", "basis", "estimated"),
    ("progress", "percentage", 10),
])
def test_forged_nested_contract_refused(tmp_path, monkeypatch, container, field, value):
    source = copy.deepcopy(product())
    source[container][field] = value
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: source)
    with pytest.raises(activity.JobActivityUnavailable):
        activity.JobActivityProfile(**config(tmp_path)).read()


@pytest.mark.parametrize("source", [None, [], {}, {"secret": "private"}])
def test_wrong_result_type_and_incomplete_result(tmp_path, monkeypatch, source):
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: source)
    with pytest.raises(activity.JobActivityUnavailable):
        activity.JobActivityProfile(**config(tmp_path)).read()


@pytest.mark.parametrize("when", ["before", "during"])
@pytest.mark.parametrize("field,value", [("authorized", False), ("actor_ref", "foreign"),
                                       ("session_ref", "foreign"), ("job_ids", ("foreign",))])
def test_frozen_config_tamper_fenced(tmp_path, monkeypatch, when, field, value):
    calls = []
    def reader(*_a, **_k):
        calls.append(True)
        if when == "during":
            object.__setattr__(profile._binding, field, value)
        return product()
    monkeypatch.setattr(activity, "build_job_activity", reader)
    profile = activity.JobActivityProfile(**config(tmp_path))
    if when == "before":
        object.__setattr__(profile._binding, field, value)
    with pytest.raises(activity.JobActivityUnavailable):
        profile.read()
    assert calls == ([] if when == "before" else [True])


def test_source_exception_fixed_and_no_output(tmp_path, monkeypatch, capsys):
    def reader(*_a, **_k):
        raise RuntimeError("password=private/path")
    monkeypatch.setattr(activity, "build_job_activity", reader)
    with pytest.raises(activity.JobActivityUnavailable) as error:
        activity.JobActivityProfile(**config(tmp_path)).read()
    assert str(error.value) == error.value.code == "job_activity_unavailable"
    assert error.value.__suppress_context__
    assert not capsys.readouterr().out


@pytest.mark.parametrize("suffix", ["../private.db", "private.db:secret"])
def test_unsafe_lexical_paths_without_source_probe(tmp_path, monkeypatch, suffix):
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: pytest.fail("read"))
    with pytest.raises(ValueError, match="^invalid_job_activity_profile$"):
        activity.JobActivityProfile(**config(tmp_path, database_path=tmp_path / suffix))


def test_unc_path_refused_without_io(tmp_path):
    with pytest.raises(ValueError, match="^invalid_job_activity_profile$"):
        activity.JobActivityProfile(**config(tmp_path, database_path=Path("//server/private.db")))


def test_constructor_does_not_open_sqlite(tmp_path, monkeypatch):
    import sqlite3
    monkeypatch.setattr(sqlite3, "connect", lambda *_a, **_k: pytest.fail("db opened"))
    activity.JobActivityProfile(**config(tmp_path))


@pytest.mark.parametrize("field", ["_reader", "_binding"])
def test_replaced_binding_or_reader_refused_without_call(tmp_path, monkeypatch, field):
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: pytest.fail("read"))
    bound = activity.JobActivityProfile(**config(tmp_path))
    replacement = (lambda *_a: product()) if field == "_reader" else copy.copy(bound._binding)
    object.__setattr__(bound, field, replacement)
    with pytest.raises(activity.JobActivityUnavailable):
        bound.read()


def test_changed_source_path_binding_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: pytest.fail("read"))
    bound = activity.JobActivityProfile(**config(tmp_path))
    object.__setattr__(bound._binding, "database_path", tmp_path / "foreign.db")
    with pytest.raises(activity.JobActivityUnavailable):
        bound.read()


def test_builder_identity_frozen_and_input_path_copied(tmp_path, monkeypatch):
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: product())
    args = config(tmp_path)
    bound = activity.JobActivityProfile(**args)
    assert bound._binding.database_path is not args["database_path"]
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: pytest.fail("changed"))
    assert bound.read() == product()


def test_explicit_response_budget_checked(tmp_path, monkeypatch):
    monkeypatch.setattr(activity, "build_job_activity", lambda *_a, **_k: product())
    monkeypatch.setattr(activity, "MAX_RESPONSE_BYTES", 1)
    with pytest.raises(activity.JobActivityUnavailable):
        activity.JobActivityProfile(**config(tmp_path)).read()


def test_uninitialized_forgery_unavailable():
    bound = object.__new__(activity.JobActivityProfile)
    with pytest.raises(activity.JobActivityUnavailable):
        bound.read()
