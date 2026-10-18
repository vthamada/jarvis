# ruff: noqa: E402
"""Explicit resume of native assist-only tasks, never replay of uncertain effects.

Operational checkpoints live in the existing job database. Answers remain owned
by canonical Core memory. Opening a runner starts nothing; all execution needs
an explicit host invocation. Scope labels are not operator authentication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from job_service import JobClaim, JobStoreError
from job_service.durable import DurableCoreJobStore
from job_service.store import DURABLE_CORE_TASK, _ref, _version
from orchestrator_service.service import OrchestratorService

from apps.jarvis_console.conversation_export import _text
from apps.jarvis_console.durable_core_receipt import find_core_receipt
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, RequestId, SessionId

SCHEMA = "jarvis-durable-core-task-v1"


def _contract(task):
    principal = f"user://{task.actor_ref}"
    return InputContract(
        request_id=RequestId(task.request_id), session_id=SessionId(task.core_session_id),
        channel=ChannelType.CONSOLE, input_type=InputType.TEXT, content=task.input_text,
        timestamp=datetime.now(UTC).isoformat(), user_id=principal,
        canonical_user_ref=principal, surface_id="surface://durable-core-task",
        surface_kind="console", surface_session_id=task.core_session_id,
        surface_capability_scope=[], operator_identity_ref=f"operator://{task.actor_ref}",
        requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
    )


def _bound(snapshot, task):
    return (
        snapshot.spec.job_id == task.job_id
        and snapshot.spec.actor_ref == task.actor_ref
        and snapshot.spec.session_ref == task.session_ref
        and snapshot.spec.task_ref == DURABLE_CORE_TASK
        and snapshot.spec.responsibility_ref == "core-durable-task"
        and snapshot.spec.max_attempts == 1
        and snapshot.spec.approved_step_ref == "input-" + task.input_sha256
        and snapshot.spec.deadline == task.deadline
        and sha256(task.input_text.encode("utf-8")).hexdigest() == task.input_sha256
    )


class DurableCoreJobRunner:
    """One native Core dispatch or readonly reconciliation; no scheduler/model port."""

    def __init__(self, store, core, worker_id):
        if (not isinstance(store, DurableCoreJobStore)
                or not isinstance(core, OrchestratorService)):
            raise JobStoreError("invalid_durable_core_composition")
        _ref(worker_id)
        self.store, self.core, self.worker_id = store, core, worker_id

    def _native_admission(self, task):
        try:
            _text(task.input_text, 2048)
        except ValueError:
            raise JobStoreError("durable_input_text_refused") from None
        engine = self.core.synthesis_engine
        if (self.core.model_tool_loop is not None
                or getattr(engine, "_generative_port", None) is not None
                or getattr(engine, "_inference_port", None) is not None):
            raise JobStoreError("durable_native_only")
        contract = _contract(task)
        directive = self.core.executive_engine.direct(contract)
        if (directive.intent not in {"analysis", "conversation", "general_assistance"}
                or directive.requires_clarification or directive.should_execute_operation):
            raise JobStoreError("durable_assist_scope_refused")
        self.core.memory_service.validate_input_subject_scope(contract)
        return contract

    @staticmethod
    def _report(snapshot, task):
        return {
            "schema_version": SCHEMA, "job": snapshot.telemetry(),
            "checkpoint_phase": task.phase, "request_id": task.request_id,
            "memory_record_id": None, "core_invoked": False,
            "canonical_final_verified": False, "result_recorded": False,
            "result_accepted": False, "recovered_result": False,
            "review_required": True, "operation_dispatched": False,
            "evidence_mode": "not_run", "error_code": None,
            "operator_authenticated": False, "action_authority": False,
            "automatic_execution": False, "cross_ledger_atomic": False,
            "exactly_once_claimed": False, "runtime_capability_promoted": False,
        }

    @staticmethod
    def _recorded(report, receipt, *, recovered):
        report.update(
            canonical_final_verified=True, result_recorded=True,
            result_accepted=receipt.outcome == "succeeded",
            recovered_result=recovered, review_required=receipt.outcome != "succeeded",
            memory_record_id=receipt.memory_record_id,
            evidence_mode="canonical_recovery" if recovered else "core_local",
        )

    def _load(self, job_id, scope):
        task = self.store.load_task(job_id, **scope)
        snapshot = self.store.get(job_id, **scope)
        if not _bound(snapshot, task):
            raise JobStoreError("durable_input_binding_refused")
        return snapshot, task

    def run_once(self, job_id, *, actor_ref, session_ref, expected_version,
                 authorized=False, lease_seconds=120):
        if authorized is not True:
            raise JobStoreError("durable_task_opt_in_required")
        for value in (job_id, actor_ref, session_ref):
            _ref(value)
        _version(expected_version)
        scope = {"actor_ref": actor_ref, "session_ref": session_ref}
        before, task = self._load(job_id, scope)
        if before.version != expected_version:
            raise JobStoreError("version_conflict")
        report = self._report(before, task)
        # Also cover a phase snapshot read just before a concurrent start commit.
        # Prepared work with an active owner cannot be reclaimed either.
        if (before.status == "running" and before.lease_until is not None
                and self.store._now() < before.lease_until.timestamp()):
            report["evidence_mode"] = "active_claim"
            return report
        # Cancellation/expiry/manual pause are not undone by an old answer.
        if before.status in {"cancelled", "expired", "failed"}:
            return report
        if task.phase == "completed":
            receipt = find_core_receipt(self.core, task)
            if receipt is None or receipt.receipt_sha256 != task.receipt_sha256:
                raise JobStoreError("durable_receipt_refused")
            self._recorded(report, receipt, recovered=True)
            return report
        if task.phase in {"started", "uncertain"}:
            if before.status == "needs_decision" and task.phase != "uncertain":
                return report
            receipt = find_core_receipt(self.core, task)
            if receipt is not None:
                final = self.store.reconcile_task(
                    job_id, expected_version=expected_version,
                    receipt_sha256=receipt.receipt_sha256, outcome=receipt.outcome, **scope,
                )
                report.update(job=final.telemetry(), checkpoint_phase="completed")
                self._recorded(report, receipt, recovered=True)
                return report
            if before.status == "running":
                expired_claim = JobClaim(
                    job_id, actor_ref, session_ref, before.worker_id,
                    before.version, before.fencing, before.lease_until,
                )
                final = self.store.mark_uncertain(expired_claim)
                report.update(job=final.telemetry(), checkpoint_phase="uncertain")
            report.update(evidence_mode="uncertain_dispatch", error_code="durable_result_unknown")
            return report
        if before.status == "needs_decision":
            return report
        # These are trusted local checks, not grants to bypass native governance.
        self._native_admission(task)
        if self.core.memory_service.repository.fetch_runtime_request_claim(
            task.request_id,
        ) is not None:
            raise JobStoreError("durable_request_already_reserved")
        claim = self.store.claim_task(
            job_id, worker_id=self.worker_id, expected_version=expected_version,
            lease_seconds=lease_seconds, **scope,
        )
        if claim is None:
            current, task = self._load(job_id, scope)
            report.update(job=current.telemetry(), checkpoint_phase=task.phase)
            return report
        try:
            current, selected = self._load(job_id, scope)
            if selected != task or not _bound(current, selected):
                raise JobStoreError("durable_input_binding_refused")
            self._native_admission(selected)
            if self.core.memory_service.repository.fetch_runtime_request_claim(task.request_id):
                raise JobStoreError("durable_request_already_reserved")
            started = self.store.start_dispatch(claim)
            contract = self._native_admission(started)
            self.store.validate_claim(claim)
            report.update(core_invoked=True, checkpoint_phase="started", evidence_mode="core_local")
            response = self.core.handle_input(contract)
            if (response.request_id != task.request_id
                    or response.session_id != task.core_session_id
                    or any(getattr(response, name, False) is not None for name in (
                        "operation_dispatch", "operation_result", "adapter_grant",
                        "adapter_grant_claim", "action_confirmation_claim",
                        "action_confirmation_challenge", "adapter_action_intent",
                    ))):
                raise JobStoreError("durable_core_result_refused")
            receipt = find_core_receipt(self.core, started)
            if (receipt is None or receipt.response_text != response.response_text
                    or receipt.memory_record_id != str(response.memory_record.memory_record_id)):
                raise JobStoreError("durable_core_result_refused")
            report["canonical_final_verified"] = True
            final = self.store.finish_task(
                claim, receipt_sha256=receipt.receipt_sha256, outcome=receipt.outcome,
            )
            self._recorded(report, receipt, recovered=False)
            report.update(job=final.telemetry(), checkpoint_phase="completed")
        except (Exception, KeyboardInterrupt):
            # No retry, new request ID, or alternative executor on this path.
            current = self.store.get(job_id, **scope)
            if current.status == "running" and current.version == claim.version:
                try:
                    checkpoint = self.store.load_task(job_id, **scope)
                    if checkpoint.phase == "started":
                        self.store.mark_uncertain(claim)
                    elif checkpoint.phase == "prepared":
                        self.store.pause(job_id, expected_version=current.version, **scope)
                except JobStoreError:
                    pass  # Concurrent cancellation/fence wins; never overwrite it.
            current, task = self._load(job_id, scope)
            report.update(job=current.telemetry(), checkpoint_phase=task.phase,
                          error_code="durable_execution_unconfirmed", review_required=True)
        return report

    def resume(self, job_id, **options):
        return self.run_once(job_id, **options)
