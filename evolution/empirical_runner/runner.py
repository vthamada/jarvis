"""Bounded, synchronous evaluation of two actually executed local ports.

The evaluator, not the candidate, owns the fixed corpus and scoring rule. Deadlines
are cooperative: an injected synchronous port cannot be preempted by this runner.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field
from typing import Callable, Literal, Protocol

EvidenceMode = Literal["fixture", "core_local", "model_real"]
_MODES = frozenset({"fixture", "core_local", "model_real"})
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,119}\Z")
CORPUS_VERSION = "exact-output-v1"


@dataclass(frozen=True)
class _Case:
    case_id: str
    split: str
    prompt: str = field(repr=False)
    expected: str


# Deliberately small, transparent contract fixture, not a benchmark of intelligence.
_CORPUS = (
    _Case("train-add", "repeat", "Return only the integer result of 17 + 25.", "42"),
    _Case("train-case", "repeat", "Return only this word in lowercase: JARVIS", "jarvis"),
    _Case("held-add", "holdout", "Return only the integer result of 31 + 16.", "47"),
    _Case("held-case", "holdout", "Return only this word in lowercase: MEMORY", "memory"),
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


CORPUS_DIGEST = _digest(
    [CORPUS_VERSION, [(c.case_id, c.split, c.prompt, c.expected) for c in _CORPUS]]
)


def _reference(value: str) -> None:
    if not isinstance(value, str) or _REF.fullmatch(value) is None:
        raise ValueError("invalid_reference")


@dataclass(frozen=True)
class EvaluationRequest:
    request_id: str
    run_id: str
    arm_id: str
    arm_revision: str
    case_id: str
    split: str
    repeat: int
    corpus_version: str
    corpus_digest: str
    input_digest: str
    prompt: str = field(repr=False)
    deadline: float
    evidence_mode: EvidenceMode


@dataclass(frozen=True)
class EvaluationResponse:
    request_id: str
    run_id: str
    arm_id: str
    arm_revision: str
    case_id: str
    split: str
    repeat: int
    corpus_version: str
    corpus_digest: str
    input_digest: str
    text: str = field(repr=False)
    evidence_mode: EvidenceMode
    status: str = "completed"

    @classmethod
    def from_request(cls, request: EvaluationRequest, text: str) -> EvaluationResponse:
        """Convenience binding, not authentication or proof of external model execution."""
        return cls(
            **{
                name: getattr(request, name)
                for name in (
                    "request_id",
                    "run_id",
                    "arm_id",
                    "arm_revision",
                    "case_id",
                    "split",
                    "repeat",
                    "corpus_version",
                    "corpus_digest",
                    "input_digest",
                    "evidence_mode",
                )
            },
            text=text,
        )


class EvaluationPort(Protocol):
    def evaluate(self, request: EvaluationRequest) -> EvaluationResponse: ...


@dataclass(frozen=True)
class Arm:
    arm_id: str
    revision: str
    evidence_mode: EvidenceMode
    port: EvaluationPort = field(repr=False)

    def __post_init__(self) -> None:
        _reference(self.arm_id)
        _reference(self.revision)
        if self.evidence_mode not in _MODES or not callable(getattr(self.port, "evaluate", None)):
            raise ValueError("invalid_arm")


@dataclass(frozen=True)
class Measurement:
    arm_id: str
    case_id: str
    split: str
    repeat: int
    passed: bool
    elapsed_seconds: float
    evidence_ref: str
    output_digest: str


@dataclass(frozen=True)
class ComparisonReport:
    run_id: str
    status: str
    reason: str
    conclusion: str
    baseline: tuple[str, str, str]
    candidate: tuple[str, str, str]
    measurements: tuple[Measurement, ...]
    expected_measurements: int

    def export_metrics(self) -> dict[str, object]:
        """Content-free bounded export: no prompt, expected answer, or generated text."""
        complete = self.status == "completed"
        arms: dict[str, object] = {}
        for name, identity in (("baseline", self.baseline), ("candidate", self.candidate)):
            groups: dict[str, object] = {}
            for split in ("repeat", "holdout"):
                items = [
                    m for m in self.measurements if m.arm_id == identity[0] and m.split == split
                ]
                groups[split] = {
                    "count": len(items),
                    "passed": sum(m.passed for m in items) if complete else None,
                    "pass_rate": sum(m.passed for m in items) / len(items) if complete else None,
                }
            arms[name] = {
                "arm_id": identity[0],
                "revision": identity[1],
                "evidence_mode": identity[2],
                "splits": groups,
            }
        return {
            "run_id": self.run_id,
            "status": self.status,
            "reason": self.reason,
            "conclusion": self.conclusion,
            "promotion_allowed": False,
            "corpus_version": CORPUS_VERSION,
            "corpus_digest": CORPUS_DIGEST,
            "expected_measurements": self.expected_measurements,
            "completed_measurements": len(self.measurements),
            "arms": arms,
            "evidence": [
                {
                    "ref": m.evidence_ref,
                    "output_digest": m.output_digest,
                    "elapsed_seconds": m.elapsed_seconds,
                }
                for m in self.measurements
            ],
        }


class EmpiricalRunner:
    def __init__(
        self,
        *,
        baseline: Arm,
        candidate: Arm,
        repeats: int = 2,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not isinstance(baseline, Arm) or not isinstance(candidate, Arm):
            raise ValueError("invalid_arm")
        if baseline.arm_id == candidate.arm_id:
            raise ValueError("distinct_arm_identity_required")
        if type(repeats) is not int or not 2 <= repeats <= 10:
            raise ValueError("repeats_out_of_bounds")
        self._baseline = baseline
        self._candidate = candidate
        self._repeats = repeats
        self._clock = clock

    def run(
        self,
        *,
        run_id: str,
        timeout_seconds: float = 30.0,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> ComparisonReport:
        _reference(run_id)
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("invalid_timeout")
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 300:
            raise ValueError("invalid_timeout")
        started = self._clock()
        if not math.isfinite(started):
            raise ValueError("invalid_clock")
        deadline = started + timeout_seconds
        measurements: list[Measurement] = []
        expected = 2 * (2 * self._repeats + 2)

        def report(status: str, reason: str) -> ComparisonReport:
            conclusion = "comparison_unavailable"
            if status == "completed":
                conclusion = (
                    "demonstration_only"
                    if "fixture" in (self._baseline.evidence_mode, self._candidate.evidence_mode)
                    else "measurement_only_no_promotion"
                )
            return ComparisonReport(
                run_id,
                status,
                reason,
                conclusion,
                (self._baseline.arm_id, self._baseline.revision, self._baseline.evidence_mode),
                (self._candidate.arm_id, self._candidate.revision, self._candidate.evidence_mode),
                tuple(measurements),
                expected,
            )

        for case in _CORPUS:
            for repeat in range(self._repeats if case.split == "repeat" else 1):
                # Alternate order to avoid a systematic baseline-first timing bias.
                arms = (self._baseline, self._candidate)
                if repeat % 2:
                    arms = tuple(reversed(arms))
                for arm in arms:
                    try:
                        if cancelled():
                            return report("inconclusive", "cancelled")
                        before = self._clock()
                        if not math.isfinite(before) or before < started:
                            return report("invalid", "invalid_clock")
                        if before >= deadline:
                            return report("inconclusive", "deadline_exceeded")
                        request_digest = _digest(
                            [
                                run_id,
                                arm.arm_id,
                                arm.revision,
                                case.case_id,
                                case.split,
                                repeat,
                                CORPUS_VERSION,
                                CORPUS_DIGEST,
                                arm.evidence_mode,
                            ]
                        )
                        request = EvaluationRequest(
                            request_digest,
                            run_id,
                            arm.arm_id,
                            arm.revision,
                            case.case_id,
                            case.split,
                            repeat,
                            CORPUS_VERSION,
                            CORPUS_DIGEST,
                            _digest(case.prompt),
                            case.prompt,
                            deadline,
                            arm.evidence_mode,
                        )
                        bindings = {
                            name: getattr(request, name)
                            for name in (
                                "request_id",
                                "run_id",
                                "arm_id",
                                "arm_revision",
                                "case_id",
                                "split",
                                "repeat",
                                "corpus_version",
                                "corpus_digest",
                                "input_digest",
                                "evidence_mode",
                            )
                        }
                        response = arm.port.evaluate(request)
                        after = self._clock()
                        if cancelled():
                            return report("inconclusive", "cancelled")
                    except Exception:
                        return report("invalid", "port_or_control_error")
                    if (
                        not isinstance(after, (int, float))
                        or isinstance(after, bool)
                        or not math.isfinite(after)
                        or after < before
                    ):
                        return report("invalid", "invalid_clock")
                    if after >= deadline:
                        return report("inconclusive", "deadline_exceeded")
                    if not isinstance(response, EvaluationResponse):
                        return report("invalid", "invalid_response")
                    if request.prompt != case.prompt or request.deadline != deadline:
                        return report("invalid", "request_tampered")
                    for name, value in bindings.items():
                        if (
                            type(getattr(response, name)) is not type(value)
                            or getattr(response, name) != value
                            or getattr(request, name) != value
                        ):
                            return report("invalid", "response_binding_mismatch")
                    if response.status != "completed":
                        return report("invalid", "incomplete_response")
                    if (
                        not isinstance(response.text, str)
                        or not 0 < len(response.text) <= 2000
                        or any(ord(c) < 32 and c not in "\r\n\t" for c in response.text)
                        or any(0xD800 <= ord(c) <= 0xDFFF for c in response.text)
                    ):
                        return report("invalid", "invalid_output")
                    measurements.append(
                        Measurement(
                            arm.arm_id,
                            case.case_id,
                            case.split,
                            repeat,
                            response.text.strip() == case.expected,
                            after - before,
                            f"empirical://{request_digest}",
                            _digest(response.text),
                        )
                    )
        if self._baseline.evidence_mode != self._candidate.evidence_mode:
            return report("inconclusive", "mixed_evidence_modes")
        return report("completed", "all_bound_cases_executed")
