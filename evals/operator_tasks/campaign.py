"""Opt-in, paired mission measurements through explicitly registered V1 ports.

This runner bounds port dispatches and rejects late results cooperatively. A
declared call budget is not proof of a port's internal model/tool enforcement.
Public synthetic cases, fixtures and small samples cannot establish SOTA.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Callable
from uuid import uuid4

from .corpus import Source
from .fixture_port import FixtureTaskPort
from .mission_corpus import CORPUS_DIGEST, VERSION, get_mission
from .mission_grader import MissionGrade, grade_mission
from .runner import Binding, ExecutionRequest, ExecutionResult, TaskPort, _identifier

_MODES = {"fixture", "injected_transport", "core_local", "model_real"}
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z", re.ASCII)
_MAX_OUTPUT_BYTES = 65536


def _reference(value):
    if (type(value) is not str or not _REF.fullmatch(value)
            or value.lower().startswith(("sk-", "sess-", "bearer-"))):
        raise ValueError("invalid_campaign_reference")


def _seconds(value, maximum):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not 0 < value <= maximum):
        raise ValueError("invalid_campaign_timeout")


@dataclass(frozen=True)
class CampaignBudget:
    timeout_seconds: float = 30.0
    max_calls: int = 1

    def __post_init__(self):
        _seconds(self.timeout_seconds, 120)
        if type(self.max_calls) is not int or self.max_calls != 1:
            raise ValueError("invalid_campaign_call_budget")


@dataclass(frozen=True)
class CampaignArm:
    """Trusted host registration, never candidate-supplied evidence of execution."""

    arm_id: str
    harness_id: str
    revision: str
    evidence_mode: str
    model_id: str | None
    provider_id: str | None
    environment_id: str
    tool_policy_id: str
    capabilities: tuple[str, ...]
    port: TaskPort = field(repr=False)
    budget: CampaignBudget = CampaignBudget()
    verify_effect: Callable | None = field(default=None, repr=False)

    def __post_init__(self):
        for value in (self.arm_id, self.harness_id, self.revision,
                      self.environment_id, self.tool_policy_id):
            _reference(value)
        for value in (self.model_id, self.provider_id):
            if value is not None:
                _reference(value)
        if (
            type(self.evidence_mode) is not str or self.evidence_mode not in _MODES
            or not _identifier(self.revision)
            or not isinstance(self.budget, CampaignBudget)
            or type(self.capabilities) is not tuple
            or len(self.capabilities) > 32
            or any(type(value) is not str or not _REF.fullmatch(value)
                   for value in self.capabilities)
            or len(set(self.capabilities)) != len(self.capabilities)
            or not callable(getattr(self.port, "execute", None))
            or getattr(self.port, "evidence_mode", None) != self.evidence_mode
            or (self.verify_effect is not None and not callable(self.verify_effect))
            or (isinstance(self.port, FixtureTaskPort) and self.evidence_mode != "fixture")
            or (self.evidence_mode == "model_real"
                and (self.model_id is None or self.provider_id is None))
        ):
            raise ValueError("invalid_campaign_arm")
        for capability in self.capabilities:
            _reference(capability)

    def metadata(self):
        return {key: getattr(self, key) for key in (
            "arm_id", "harness_id", "revision", "evidence_mode", "model_id",
            "provider_id", "environment_id", "tool_policy_id",
        )} | {
            "capabilities": list(self.capabilities), "budget": asdict(self.budget),
            "internal_call_budget": "declared_only", "budget_enforcement_verified": False,
        }


@dataclass(frozen=True)
class CampaignMeasurement:
    arm_id: str
    case_id: str
    category: str
    split: str
    repeat: int
    status: str
    outcome: str
    success: bool = False
    passed: tuple[str, ...] = ()
    failed: tuple[str, ...] = ()
    elapsed_ms: int | None = None
    input_units: int | None = None
    output_units: int | None = None


@dataclass(frozen=True)
class CampaignReport:
    status: str
    reason: str
    arms: tuple[CampaignArm, CampaignArm] = field(repr=False)
    measurements: tuple[CampaignMeasurement, ...]
    expected_measurements: int
    repeats: int
    declared_conditions_match: bool
    port_dispatches: int
    elapsed_ms: int | None

    def export_metrics(self):
        arms = []
        gaps = []
        for arm in self.arms:
            cells = [item for item in self.measurements if item.arm_id == arm.arm_id]
            executed = [item for item in cells if item.status == "executed"]
            successes = sum(item.success for item in cells)

            def units(name):
                values = [getattr(item, name) for item in executed]
                return sum(values) if values and all(v is not None for v in values) else None

            arms.append(arm.metadata() | {
                "denominator_total": len(cells), "executed": len(executed),
                "not_run": sum(item.status == "not_run" for item in cells),
                "unsupported": sum(item.outcome == "unsupported" for item in cells),
                "passed": successes, "success_rate_total": successes / len(cells),
                "input_units": units("input_units"), "output_units": units("output_units"),
                "model_calls": None, "tool_calls": None, "cost": None,
            })
            for case_id in dict.fromkeys(item.case_id for item in cells):
                missing = sorted(set(get_mission(case_id).required_capabilities)
                                 - set(arm.capabilities))
                if missing:
                    gaps.append({"arm_id": arm.arm_id, "case_id": case_id,
                                 "missing_capabilities": missing,
                                 "denominator_measurements": self.repeats})
        modes = {arm.evidence_mode for arm in self.arms}
        comparison = (
            "matched_configuration_only" if self.declared_conditions_match else "not_comparable"
        )
        if modes == {"fixture"}:
            comparison = "control_only"
        return {
            "schema_version": "jarvis-mission-campaign-v1",
            "corpus_version": VERSION, "corpus_digest": CORPUS_DIGEST,
            "status": self.status, "reason": self.reason,
            "expected_measurements": self.expected_measurements,
            "reported_measurements": len(self.measurements),
            "repeats": self.repeats, "port_dispatches": self.port_dispatches,
            "elapsed_ms": self.elapsed_ms, "arms": arms,
            "capability_gaps": gaps,
            "measurements": [asdict(item) for item in self.measurements],
            "declared_conditions_match": self.declared_conditions_match,
            "comparison_status": comparison, "paired_budget_execution_verified": False,
            "internal_call_budget_enforcement": "not_observed",
            "winner": None, "sota_claim": False, "improvement_claim": False,
            "promotion_allowed": False, "requires_human_review": True,
            "sample_limitations": "small_public_synthetic_corpus",
            "deadline_enforcement": "cooperative_return_time_check",
        }


class _Stopped(Exception):
    def __init__(self, code):
        self.code = code


class MissionCampaign:
    """Fixed host selection, fresh bindings, no oracle or executable task payload."""

    def __init__(self, *, baseline: CampaignArm, candidate: CampaignArm,
                 repeats: int = 2, clock: Callable[[], float] = time.monotonic):
        if (not isinstance(baseline, CampaignArm) or not isinstance(candidate, CampaignArm)
                or baseline.arm_id == candidate.arm_id
                or type(repeats) is not int or not 2 <= repeats <= 5 or not callable(clock)):
            raise ValueError("invalid_campaign")
        self.arms, self.repeats, self.clock = (baseline, candidate), repeats, clock

    def run(self, case_ids: tuple[str, ...], *, run_id: str, authorized=False,
            timeout_seconds: float = 900, max_executions: int = 250,
            cancelled: Callable[[], bool] = lambda: False) -> CampaignReport:
        if authorized is not True:
            raise ValueError("mission_campaign_opt_in_required")
        _reference(run_id)
        if not _identifier(run_id):
            raise ValueError("invalid_campaign_reference")
        _seconds(timeout_seconds, 3600)
        if (type(case_ids) is not tuple or not 1 <= len(case_ids) <= 25
                or any(type(case_id) is not str for case_id in case_ids)
                or len(set(case_ids)) != len(case_ids)
                or type(max_executions) is not int or not 1 <= max_executions <= 250
                or not callable(cancelled)):
            raise ValueError("invalid_campaign_selection")
        missions = tuple(get_mission(case_id) for case_id in case_ids)
        # Freeze selection before calling any port. Alternate across cases *and*
        # repeats so repeat zero does not always privilege the baseline.
        schedule = []
        for index, mission in enumerate(missions):
            for repeat in range(self.repeats):
                arms = self.arms if (index + repeat) % 2 == 0 else tuple(reversed(self.arms))
                schedule.extend((arm, mission, repeat) for arm in arms)
        previous = self.clock()
        if type(previous) not in (int, float) or not math.isfinite(previous):
            raise ValueError("invalid_campaign_clock")
        started, deadline = previous, previous + timeout_seconds
        measurements = []
        dispatches, stop = 0, None

        def check():
            nonlocal previous
            try:
                state, now = cancelled(), self.clock()
            except Exception:
                raise _Stopped("control_error") from None
            if type(state) is not bool:
                raise _Stopped("control_error")
            if type(now) not in (int, float) or not math.isfinite(now) or now < previous:
                raise _Stopped("invalid_clock")
            previous = now
            if state:
                raise _Stopped("cancelled")
            if now >= deadline:
                raise _Stopped("deadline_exceeded")
            return now

        def cell(arm, mission, repeat, status, outcome, **values):
            return CampaignMeasurement(arm.arm_id, mission.case_id, mission.category,
                                       mission.split, repeat, status, outcome, **values)

        for arm, mission, repeat in schedule:
            if stop is not None:
                measurements.append(cell(arm, mission, repeat, "not_run", stop))
                continue
            try:
                before = check()
            except _Stopped as error:
                stop = error.code
                measurements.append(cell(arm, mission, repeat, "not_run", stop))
                continue
            if not set(mission.required_capabilities) <= set(arm.capabilities):
                measurements.append(cell(arm, mission, repeat, "not_run", "unsupported"))
                continue
            if dispatches >= max_executions:
                stop = "execution_limit"
                measurements.append(cell(arm, mission, repeat, "not_run", stop))
                continue
            binding = Binding(run_id, uuid4().hex, mission.case_id, mission.version,
                              mission.digest, arm.revision, "campaign-subject-" + uuid4().hex,
                              "campaign-session-" + uuid4().hex)
            execution_deadline = min(deadline, before + arm.budget.timeout_seconds)
            request = ExecutionRequest(binding, mission.brief,
                tuple(Source(source.ref, source.text) for source in mission.sources),
                execution_deadline, None)
            expected = (binding, request.brief, request.sources, request.deadline, request.history)
            expected_sources = tuple(asdict(source) for source in request.sources)
            # Preserve independent copies: a trusted callback may still mutate a
            # frozen Python object via object.__setattr__.
            expected_binding = asdict(binding)
            dispatches += 1
            result, port_error = None, False
            try:
                result = arm.port.execute(request)
            except Exception:
                port_error = True
            try:
                after = check()
            except _Stopped as error:
                stop = error.code
                measurements.append(cell(arm, mission, repeat, "executed", stop))
                continue
            elapsed = max(0, round((after - before) * 1000))
            failure = None
            if after >= execution_deadline:
                failure = "execution_deadline_exceeded"
            elif port_error:
                failure = "port_error"
            elif ((request.binding, request.brief, request.sources,
                   request.deadline, request.history)
                  != expected or asdict(request.binding) != expected_binding
                  or tuple(asdict(source) for source in request.sources) != expected_sources):
                failure = "request_tampered"
            elif (not isinstance(result, ExecutionResult) or result.binding != binding
                  or asdict(result.binding) != expected_binding
                  or type(result.status) is not str
                  or result.status not in {"completed", "needs_decision", "incomplete", "error"}
                  or type(result.payload) is not bytes or len(result.payload) > _MAX_OUTPUT_BYTES
                  or not self._usage(result.input_units) or not self._usage(result.output_units)
                  or type(result.history_digest) is not str):
                failure = "binding_or_metadata_refused"
            if failure is not None:
                measurements.append(cell(arm, mission, repeat, "executed", failure,
                                         elapsed_ms=elapsed))
                continue
            if result.status != "completed":
                measurements.append(cell(arm, mission, repeat, "executed", result.status,
                    elapsed_ms=elapsed, input_units=result.input_units,
                    output_units=result.output_units))
                continue
            try:
                score = grade_mission(mission, binding, result,
                    available_capabilities=arm.capabilities, verify_effect=arm.verify_effect)
                if check() >= execution_deadline:
                    raise ValueError("grading_deadline_exceeded")
                if (not isinstance(score, MissionGrade) or type(score.success) is not bool
                        or score.outcome not in {
                            "passed", "needs_rework", "blocked", "invalid_output",
                        }
                        or type(score.passed) is not tuple or type(score.failed) is not tuple
                        or any(type(name) is not str or not _REF.fullmatch(name)
                               for name in (*score.passed, *score.failed))
                        or score.success != (score.outcome == "passed" and not score.failed)):
                    raise ValueError("invalid_grade")
            except _Stopped as error:
                stop = error.code
                measurements.append(cell(arm, mission, repeat, "executed", stop,
                                         elapsed_ms=elapsed))
                continue
            except Exception:
                measurements.append(cell(arm, mission, repeat, "executed", "grading_error",
                                         elapsed_ms=elapsed))
                continue
            measurements.append(cell(arm, mission, repeat, "executed", score.outcome,
                success=score.success, passed=score.passed, failed=score.failed,
                elapsed_ms=elapsed, input_units=result.input_units,
                output_units=result.output_units))
        match_fields = ("evidence_mode", "model_id", "provider_id", "environment_id",
                        "tool_policy_id", "budget")
        matched = all(getattr(self.arms[0], key) == getattr(self.arms[1], key)
                      for key in match_fields)
        elapsed = (
            None if stop in {"invalid_clock", "control_error"}
            else round((previous - started) * 1000)
        )
        return CampaignReport("completed" if stop is None else "inconclusive",
            "all_selected_cells_accounted" if stop is None else stop, self.arms,
            tuple(measurements), len(schedule), self.repeats, matched, dispatches, elapsed)

    @staticmethod
    def _usage(value):
        return value is None or type(value) is int and 0 <= value <= 10_000_000
