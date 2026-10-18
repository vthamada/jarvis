"""Operator review hints never authorize canonical memory mutations."""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from memory_service.recall import RecallScope, RecallSourceState, turn_source_ref
from memory_service.repository import StoredTurn
from memory_service.retention_review import build_retention_review

NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
SCOPE = RecallScope("private-subject", ("private-session",), NOW)


def row(age=0, **changes):
    return replace(StoredTurn(
        "private-session", "private-mission", "private-subject", "private-request",
        "report", "private-response", (NOW - timedelta(seconds=age)).isoformat(),
        plan_steps=["private-plan-step"],
    ), **changes)


def test_age_is_operator_review_horizon_not_retention_permission():
    old, boundary, fresh = row(101), row(100), row(99)
    result = build_retention_review([old, boundary, fresh], scope=SCOPE,
                                    max_age_seconds=100)
    assert result.status == "review_ready"
    assert len(result.items) == 1
    assert result.items[0].source_ref == turn_source_ref(old)
    assert result.items[0].reasons == ("age_horizon_exceeded",)
    assert result.unchanged_count == 2
    report = result.metadata()
    assert report["review_only"] is True
    assert report["mutation_performed"] is False
    assert report["authority"] == "none"
    for secret in ("private-subject", "private-session", "private-request",
                   "private-response", "private-plan-step", turn_source_ref(old)):
        assert secret not in json.dumps(report)
    assert result.metadata(include_refs=True)["items"][0]["source_ref"] == turn_source_ref(old)


@pytest.mark.parametrize("state,reason", [
    (RecallSourceState(status="stale"), "declared_stale"),
    (RecallSourceState(status="revoked"), "declared_revoked"),
    (RecallSourceState(expires_at=NOW), "expired"),
])
def test_declared_lifecycle_is_only_a_review_signal(state, reason):
    source = row()
    result = build_retention_review([source], scope=SCOPE,
                                    source_states={turn_source_ref(source): state})
    assert result.status == "review_ready"
    assert result.items[0].reasons == (reason,)
    assert result.metadata()["mutation_performed"] is False


def test_valid_explicit_correction_is_not_inferred_from_prose():
    old, new = row(20), row(10, request_content="This supersedes the old source")
    states = {turn_source_ref(new): RecallSourceState(
        version=2, supersedes_ref=turn_source_ref(old))}
    result = build_retention_review([new, old], scope=SCOPE, source_states=states)
    assert result.items[0].source_ref == turn_source_ref(old)
    assert result.items[0].reasons == ("explicitly_superseded",)
    assert result.unchanged_count == 1
    assert build_retention_review([old, new], scope=SCOPE).status == "empty"


@pytest.mark.parametrize("changes", [
    {"version": 1}, {"version": 0}, {"version": True}, {"status": "revoked"},
    {"status": "stale"},
    {"expires_at": NOW}, {"supersedes_ref": "stored-turn:sha256:" + "0" * 64},
])
def test_invalid_or_unavailable_correction_never_resolves_old_source(changes):
    old, new = row(20), row(10)
    state = replace(RecallSourceState(version=2, supersedes_ref=turn_source_ref(old)),
                    **changes)
    result = build_retention_review([old, new], scope=SCOPE,
                                    source_states={turn_source_ref(new): state})
    assert result.status in {"needs_decision", "rejected"}
    assert all("explicitly_superseded" not in item.reasons for item in result.items)


def test_competing_correction_branches_withhold_entire_component():
    old, left, right = row(30), row(20), row(10)
    states = {turn_source_ref(child): RecallSourceState(
        version=2, supersedes_ref=turn_source_ref(old)) for child in (left, right)}
    result = build_retention_review([old, left, right], scope=SCOPE, source_states=states)
    assert result.status == "needs_decision"
    assert result.withheld_count == 3
    assert all(item.reasons == ("ambiguous_correction",) for item in result.items)


def test_reversed_correction_time_and_cycles_are_not_resolved():
    old, new = row(10), row(20)
    states = {turn_source_ref(new): RecallSourceState(
        version=2, supersedes_ref=turn_source_ref(old))}
    assert build_retention_review([old, new], scope=SCOPE,
                                  source_states=states).status == "needs_decision"
    states[turn_source_ref(old)] = RecallSourceState(
        version=3, supersedes_ref=turn_source_ref(new))
    result = build_retention_review([old, new], scope=SCOPE, source_states=states)
    assert all("explicitly_superseded" not in item.reasons for item in result.items)


@pytest.mark.parametrize("timestamp", ["nonsense", "2026-10-13T11:00:00",
                                       "2026-10-13T14:00:00Z"])
def test_invalid_or_future_timestamp_is_withheld(timestamp):
    result = build_retention_review([row(timestamp=timestamp)], scope=SCOPE)
    assert result.status == "needs_decision"
    assert result.withheld_count == 1
    assert not result.items


@pytest.mark.parametrize("changes", [{"user_id": "foreign"}, {"session_id": "foreign"}])
def test_foreign_rows_are_never_hashed_or_content_inspected(monkeypatch, changes):
    import memory_service.retention_review as module
    foreign = row(request_content=object(), plan_steps=object(), **changes)
    monkeypatch.setattr(module, "turn_source_ref", lambda _: pytest.fail("foreign hash"))
    result = build_retention_review([foreign], scope=SCOPE)
    assert result.status == "empty"
    assert result.scoped_count == 0


@pytest.mark.parametrize("timestamp", ["invalid", "2026-10-13T14:00:00Z"])
def test_unobservable_correction_withholds_known_parent(timestamp):
    old, new = row(20), row(timestamp=timestamp)
    result = build_retention_review([old, new], scope=SCOPE, source_states={
        turn_source_ref(new): RecallSourceState(version=2, supersedes_ref=turn_source_ref(old)),
    })
    assert result.status == "needs_decision" and result.withheld_count == 2
    assert result.items[0].source_ref == turn_source_ref(old)
    assert result.items[0].reasons == ("ambiguous_correction",)


def test_metadata_copies_cannot_mutate_plan_and_refs_require_boolean_opt_in():
    result = build_retention_review([row(100)], scope=SCOPE, max_age_seconds=50)
    metadata = result.metadata(include_refs=True)
    metadata["items"][0]["reasons"].clear()
    assert result.items[0].reasons == ("age_horizon_exceeded",)
    with pytest.raises(ValueError, match="invalid_include_refs"):
        result.metadata(include_refs="yes")


@pytest.mark.parametrize("kwargs,reason", [
    ({"max_candidates": True}, "invalid_limits"),
    ({"max_candidates": 0}, "invalid_limits"),
    ({"max_candidates": 1001}, "invalid_limits"),
    ({"max_age_seconds": -1}, "invalid_limits"),
    ({"max_age_seconds": True}, "invalid_limits"),
    ({"deadline_monotonic": float("nan")}, "invalid_limits"),
    ({"deadline_monotonic": float("inf")}, "invalid_limits"),
    ({"scope": replace(SCOPE, session_ids=())}, "invalid_scope"),
    ({"scope": replace(SCOPE, now=NOW.replace(tzinfo=None))}, "invalid_scope"),
    ({"scope": replace(SCOPE, session_ids=("private-session",) * 2)}, "invalid_scope"),
    ({"source_states": {"not-a-ref": RecallSourceState()}}, "invalid_source_states"),
])
def test_invalid_configuration_has_no_partial_result(kwargs, reason):
    result = build_retention_review([row(4000000)], **({"scope": SCOPE} | kwargs))
    assert result.status == "rejected"
    assert result.reason == reason
    assert result.plan_hash is None
    assert result.items == ()
    assert result.inspected_count == result.scoped_count == 0


def test_exhausted_iterable_budget_discards_partial():
    result = build_retention_review([row(100), row(200)], scope=SCOPE,
                                    max_candidates=1, max_age_seconds=50)
    assert result.reason == "candidate_budget_exceeded"
    assert result.items == () and result.plan_hash is None


def test_source_exception_cancellation_deadline_discard_partial():
    def broken():
        yield row(100)
        raise RuntimeError("secret-error")
    result = build_retention_review(broken(), scope=SCOPE)
    assert result.reason == "source_unavailable"
    assert "secret-error" not in repr(result)
    checks = iter([False, False, True])
    result = build_retention_review([row(100), row(200)], scope=SCOPE,
                                    cancelled=lambda: next(checks))
    assert result.status == "cancelled"
    assert result.items == () and result.plan_hash is None
    assert build_retention_review([row()], scope=SCOPE, deadline_monotonic=1,
                                  monotonic_clock=lambda: 1).reason == "deadline_exceeded"
    invalid_clock = build_retention_review([], scope=SCOPE, deadline_monotonic=1,
                                           monotonic_clock=lambda: float("nan"))
    assert invalid_clock.reason == "control_unavailable"


def test_mutable_states_and_plan_steps_are_snapshotted():
    source = row(100)
    states = {turn_source_ref(source): RecallSourceState(status="stale")}
    expected = build_retention_review([source], scope=SCOPE, source_states=states)
    def mutate_after_snapshot():
        states.clear()
        return False
    result = build_retention_review([source], scope=SCOPE, source_states=states,
                                    cancelled=mutate_after_snapshot)
    assert result == expected
    encoded = json.dumps(result.metadata(include_refs=True), sort_keys=True)
    source.plan_steps.append("changed-after-planning")
    assert json.dumps(result.metadata(include_refs=True), sort_keys=True) == encoded
    with pytest.raises((AttributeError, TypeError)):
        result.items[0].version = 99


def test_hash_is_stable_for_permutations_duplicates_and_changes_for_horizon():
    first, second = row(100), row(200)
    result = build_retention_review([first, second], scope=SCOPE, max_age_seconds=50)
    assert result.plan_hash == build_retention_review(
        [second, first], scope=SCOPE, max_age_seconds=50).plan_hash
    assert len(build_retention_review([first, first], scope=SCOPE,
                                     max_age_seconds=50).items) == 1
    assert result.plan_hash != build_retention_review(
        [first, second], scope=SCOPE, max_age_seconds=60).plan_hash


@pytest.mark.parametrize("changes", [
    {"request_content": "x" * 65537}, {"plan_steps": ["x"] * 101},
    {"plan_steps": [object()]}, {"mission_id": object()}, {"timestamp": object()},
])
def test_bad_or_oversized_scoped_sources_fail_closed(changes):
    result = build_retention_review([row(100), row(**changes)], scope=SCOPE)
    assert result.status == "rejected"
    assert result.items == () and result.plan_hash is None
