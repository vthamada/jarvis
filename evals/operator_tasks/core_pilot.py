"""Opt-in real-Core execution of the corpus in disposable canonical stores."""

from __future__ import annotations

import argparse
import json
import math
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from .corpus import CORRECTION, INITIAL, TASKS, get_task
from .runner import (
    Binding,
    ExecutionRequest,
    ExecutionResult,
    History,
    OperatorTaskRunner,
    Registration,
    _identifier,
)


class IsolatedOperatorCorePort:
    """Real synthesis only: never rewrite a Core answer to make the scorer pass.

    Imports existing trusted pilot composition lazily. No user database, provider,
    tracing adapter, broad tool action, authentication or capability promotion.
    """

    evidence_mode = "core_local"

    def __init__(self, core, *, subject_ref="operator-task-subject", revision="core-control-v1"):
        if not _identifier(subject_ref) or not _identifier(revision):
            raise ValueError("core_context_refused")
        self.core = core
        self.subject_ref = subject_ref
        self.revision = revision
        self.turn_count = 0
        self.canonical_final_count = 0
        self.event_count = 0
        self.governance_decisions = {}

    def execute(self, request):
        self._validate(request)
        from apps.jarvis_console.memory_recall_pilot import PilotContext, RecallPilotPort

        binding = request.binding
        history_digest = ""
        if request.history:
            # Seed two public turns under the previous session; do not change recall policy.
            previous = PilotContext(self.subject_ref, request.history.prior_session_ref)
            for index, source in enumerate((INITIAL, CORRECTION)):
                if time.monotonic() >= request.deadline:
                    return ExecutionResult(binding, "incomplete")
                self._interact(
                    RecallPilotPort(self.core, previous),
                    previous.input(f"{binding.request_id}-seed-{index}", source.text),
                )
            history_digest = request.history.digest
        context = PilotContext(self.subject_ref, binding.session_ref)
        if time.monotonic() >= request.deadline:
            return ExecutionResult(binding, "incomplete")
        prompt = request.brief
        if not request.history:
            prompt += "\n" + "\n".join(f"{s.ref}: {s.text}" for s in request.sources)
        prompt += "\nJSON envelope binding: " + json.dumps(asdict(binding), sort_keys=True)
        metadata = self._interact(
            RecallPilotPort(self.core, context), context.input(binding.request_id, prompt)
        )
        # Fetch the exact final written by sovereign synthesis, not a parallel answer.
        turns = self.core.memory_service.repository.fetch_recent_turns(binding.session_ref, 20)
        payload = turns[-1].response_text.encode("utf-8")
        decision = metadata["governance_decision"]
        if decision != "allow":
            return ExecutionResult(binding, "needs_decision", history_digest=history_digest)
        return ExecutionResult(binding, "completed", payload, history_digest)

    def _validate(self, request):
        if not isinstance(request, ExecutionRequest) or not isinstance(request.binding, Binding):
            raise ValueError("core_binding_refused")
        binding = request.binding
        task = get_task(binding.case_id)
        if (
            binding.subject_ref != self.subject_ref
            or binding.revision != self.revision
            or binding.task_version != task.version
            or binding.task_digest != task.digest
            or request.sources != task.sources
            or request.brief != task.brief
            or not _identifier(binding.run_id)
            or not _identifier(binding.request_id)
            or not _identifier(binding.session_ref)
            or type(request.deadline) not in (int, float)
            or not math.isfinite(request.deadline)
            or not time.monotonic() < request.deadline <= time.monotonic() + 120
        ):
            raise ValueError("core_binding_refused")
        # Reuse the runner's subject/session/correction guard without executing a candidate.
        validator = OperatorTaskRunner(
            Registration(self, self.evidence_mode, self.revision, self.subject_ref)
        )
        validator._validate_history(task, binding.session_ref, request.history)

    def _interact(self, port, contract):
        metadata = port.interact(contract)
        self.turn_count += 1
        self.canonical_final_count += 1
        self.event_count += metadata["core_event_count"]
        decision = metadata["governance_decision"]
        self.governance_decisions[decision] = self.governance_decisions.get(decision, 0) + 1
        return metadata


def run_core_operator_tasks(*, authorized=False):
    if authorized is not True:
        raise ValueError("operator_tasks_opt_in_required")
    base = Path(tempfile.gettempdir()).resolve()
    workspace = Path(__file__).resolve().parents[2]
    if base == workspace or base.is_relative_to(workspace):
        raise ValueError("operator_tasks_temp_base_refused")
    from apps.jarvis_console.voice_pilot import _isolated_core

    measurements = []
    turns = finals = events = 0
    decisions = {}
    # Isolate every case to avoid cross-case contamination and persistent user data.
    for index, task in enumerate(TASKS):
        with TemporaryDirectory(prefix="jarvis-operator-tasks-", dir=str(base)) as runtime:
            port = IsolatedOperatorCorePort(_isolated_core(Path(runtime)))
            runner = OperatorTaskRunner(
                Registration(port, "core_local", port.revision, port.subject_ref)
            )
            session = f"operator-task-session-{index}"
            history = (
                History(
                    port.subject_ref,
                    "operator-task-prior",
                    session,
                    "operator-task-correction-v2",
                    CORRECTION.ref,
                )
                if task.product_kind == "resumption"
                else None
            )
            measurements.append(
                runner.run(
                    task.case_id,
                    run_id="operator-task-core-control",
                    session_ref=session,
                    timeout_seconds=120,
                    history=history,
                ).export()
            )
            turns += port.turn_count
            finals += port.canonical_final_count
            events += port.event_count
            for decision, count in port.governance_decisions.items():
                decisions[decision] = decisions.get(decision, 0) + count
    return {
        "evidence_mode": "core_local",
        "measurements": measurements,
        "core_turn_count": turns,
        "canonical_final_count": finals,
        "core_event_count": events,
        "governance_decisions": decisions,
        "runtime_mode": "temporary_sqlite",
        "operator_authenticated": False,
        "external_model_used": False,
        "production_memory_opened": False,
        "operation_dispatched": False,
        "promotion_allowed": False,
        "improvement_claim": False,
        "useful_continuity_demonstrated": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args(argv)
    if not args.authorized:
        parser.error("operator_tasks_opt_in_required")
    print(json.dumps(run_core_operator_tasks(authorized=True), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
