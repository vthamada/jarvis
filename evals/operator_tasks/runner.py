"""Bound execution ports and content-free measurements for product task evaluation."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import asdict, dataclass
from typing import Callable, Protocol
from uuid import uuid4

from .corpus import CORPUS_DIGEST, VERSION, Source, get_task
from .evaluator import MAX_OUTPUT_BYTES, decode_product, score_product

EVIDENCE_MODES = ("fixture", "core_local", "model_real")


@dataclass(frozen=True)
class Binding:
    run_id: str
    request_id: str
    case_id: str
    task_version: str
    task_digest: str
    revision: str
    subject_ref: str
    session_ref: str


@dataclass(frozen=True)
class History:
    subject_ref: str
    prior_session_ref: str
    current_session_ref: str
    correction_receipt: str
    correction_source_ref: str

    @property
    def digest(self):
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ExecutionRequest:
    binding: Binding
    brief: str
    sources: tuple[Source, ...]
    deadline: float
    history: History | None


@dataclass(frozen=True)
class ExecutionResult:
    """Port-observed outcome, separate from candidate JSON and candidate claims."""

    binding: Binding
    status: str
    payload: bytes = b""
    history_digest: str = ""
    input_units: int | None = None
    output_units: int | None = None


class TaskPort(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...


@dataclass(frozen=True)
class Registration:
    """Trusted composition only; do not build this from a model response or open endpoint.

    `model_real` requires an actual provider port and independently observed usage.
    This package has no such provider and makes no model-real evidence claim.
    """

    port: TaskPort
    evidence_mode: str
    revision: str
    subject_ref: str


@dataclass(frozen=True)
class Measurement:
    case_id: str
    evidence_mode: str
    outcome: str
    success: bool
    criteria_passed: int
    criteria_failed: int
    failed_criteria: tuple[str, ...]
    elapsed_ms: int
    input_units: int | None
    output_units: int | None
    rework_required: bool

    def export(self):
        # No subject/session/run ids, prompts, narrative, source spans or artifacts.
        return asdict(self) | {
            "task_version": VERSION,
            "corpus_digest": CORPUS_DIGEST,
            "promotion_allowed": False,
            "improvement_claim": False,
            "requires_human_review": True,
        }


def _identifier(value):
    return type(value) is str and bool(re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value))


class OperatorTaskRunner:
    """One-shot bound runs; synchronous ports must honor the supplied deadline.

    The return-time check rejects late output, not a hard process preemption.
    External/in-process untrusted execution needs separate OS containment.
    """

    def __init__(
        self,
        registration: Registration,
        *,
        clock: Callable[[], float] = time.monotonic,
    ):
        if (
            not isinstance(registration, Registration)
            or registration.evidence_mode not in EVIDENCE_MODES
            or not _identifier(registration.revision)
            or not _identifier(registration.subject_ref)
            or not callable(getattr(registration.port, "execute", None))
            or getattr(registration.port, "evidence_mode", registration.evidence_mode)
            != registration.evidence_mode
        ):
            raise ValueError("invalid_registration")
        self.registration = registration
        self.clock = clock

    def run(
        self,
        case_id: str,
        *,
        run_id: str,
        session_ref: str,
        timeout_seconds: float = 30.0,
        history: History | None = None,
    ) -> Measurement:
        task = get_task(case_id)
        if (
            not _identifier(run_id)
            or not _identifier(session_ref)
            or type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or not 0 < timeout_seconds <= 120
        ):
            raise ValueError("invalid_run")
        self._validate_history(task, session_ref, history)
        start = self._time()
        binding = Binding(
            run_id,
            uuid4().hex,
            task.case_id,
            task.version,
            task.digest,
            self.registration.revision,
            self.registration.subject_ref,
            session_ref,
        )
        request = ExecutionRequest(
            binding, task.brief, task.sources, start + timeout_seconds, history
        )
        try:
            result = self.registration.port.execute(request)
        except Exception:
            return self._failure(task, "port_error", start)
        end = self._time()
        if end < start or end >= request.deadline:
            return self._failure(task, "deadline_exceeded", start, end)
        if (
            not isinstance(result, ExecutionResult)
            or result.binding != binding
            or result.status not in ("completed", "needs_decision", "incomplete", "error")
            or not self._usage_valid(result.input_units)
            or not self._usage_valid(result.output_units)
            or type(result.payload) is not bytes
            or len(result.payload) > MAX_OUTPUT_BYTES
            or type(result.history_digest) is not str
        ):
            return self._failure(task, "binding_or_metadata_refused", start, end)
        if result.status != "completed":
            return self._failure(task, result.status, start, end, result)
        try:
            raw_binding, product = decode_product(result.payload)
        except ValueError:
            return self._failure(task, "invalid_output", start, end, result)
        if raw_binding != asdict(binding) or product.kind != task.product_kind:
            return self._failure(task, "stale_or_tampered_output", start, end, result)
        score = score_product(
            task,
            product,
            prior_session_ref=history.prior_session_ref if history else "",
            correction_receipt=history.correction_receipt if history else "",
            history_verified=bool(history and result.history_digest == history.digest),
        )
        return Measurement(
            case_id,
            self.registration.evidence_mode,
            "passed" if score.success else "needs_rework",
            score.success,
            len(score.passed),
            len(score.failed),
            score.failed,
            round((end - start) * 1000),
            result.input_units,
            result.output_units,
            not score.success,
        )

    def _validate_history(self, task, session_ref, history):
        if task.product_kind != "resumption":
            if history is not None:
                raise ValueError("unexpected_history")
            return
        if (
            not isinstance(history, History)
            or history.subject_ref != self.registration.subject_ref
            or history.current_session_ref != session_ref
            or history.prior_session_ref == session_ref
            or not _identifier(history.prior_session_ref)
            or not _identifier(history.correction_receipt)
            or history.correction_source_ref != "correction-rev2"
        ):
            raise ValueError("history_binding_refused")

    def _time(self):
        now = self.clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ValueError("invalid_clock")
        return now

    @staticmethod
    def _usage_valid(value):
        return value is None or type(value) is int and 0 <= value <= 10000000

    def _failure(self, task, outcome, start, end=None, result=None):
        elapsed = (self._time() if end is None else end) - start
        return Measurement(
            task.case_id,
            self.registration.evidence_mode,
            outcome,
            False,
            0,
            1,
            ("complete_bound_product",),
            max(0, round(elapsed * 1000)),
            result.input_units if result else None,
            result.output_units if result else None,
            True,
        )
