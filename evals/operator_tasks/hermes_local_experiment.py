"""Explicit synthetic loopback comparison; default preflight performs no inference.

This lab does not install/start/discover models, load credentials, retry, repair
outputs or promote capabilities. A loopback service can forward data upstream;
execution therefore requires a separate acknowledgement. Experiment artifacts
are not canonical memory. Only the existing Core selects conversational history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from inference_service.chat_completions_provider import (  # noqa: E402
    ChatCompletionsInferenceProvider,
)
from inference_service.local_chat_transport import LocalChatHttpTransport  # noqa: E402

from apps.jarvis_console.conversation_export import export_conversation  # noqa: E402
from apps.jarvis_console.local_model_tool_loop_cli import (  # noqa: E402
    OUTPUT_SCHEMA,
    _host_selection,
    _PhaseDiagnostics,
)
from apps.jarvis_console.model_tool_loop_cli import _run_report_loop  # noqa: E402
from apps.jarvis_console.runtime import ConsoleRuntime  # noqa: E402
from apps.jarvis_console.voice_pilot import _isolated_core  # noqa: E402
from evals.operator_tasks.hermes_comparison import (  # noqa: E402
    PREFERENCE,
    PUBLIC_CASE_DIGEST,
    CanonicalReadback,
    ComparisonConfig,
    TurnExecution,
    compare_conversations,
    run_conversation_arm,
)
from evals.operator_tasks.inference_guard import CampaignInferenceGuard  # noqa: E402

MODEL = "qwen3:4b-instruct"
ENDPOINT = "http://127.0.0.1:11434/v1/chat/completions"
SESSION = "hermes-synthetic-comparison"
MAX_ATTEMPTS = 24
_PROVIDER = "chat_completions_local"


def _save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, allow_nan=False, indent=2) + "\n",
                    encoding="utf-8")


def preflight(*, directory: Path, endpoint: str = ENDPOINT, model: str = MODEL):
    """Lexical host selection only; no endpoint call, model or runtime creation."""
    if not isinstance(directory, Path) or not directory.is_absolute():
        raise ValueError("invalid_experiment_directory")
    _host_selection(
        reports={"documentation": directory / "unused-report.txt"},
        endpoint=endpoint, model=model, session_id=SESSION, authorized=True,
        confirmed=True, reports_confirmed=True, upstream_egress_acknowledged=True,
        timeout_seconds=120, include_content=True,
    )
    return {
        "schema_version": "jarvis-hermes-local-experiment-v1", "status": "preflight",
        "corpus_digest": PUBLIC_CASE_DIGEST, "max_inference_attempts": MAX_ATTEMPTS,
        "attempted_inferences": 0, "automatic_retry": False, "warmup_calls": 0,
        "account_used": False, "paid_fallback": False, "runtime_capability_promoted": False,
        "real_model_verified": False, "upstream_egress_possible": True,
    }


def run_local_experiment(*, directory: Path, endpoint: str = ENDPOINT, model: str = MODEL,
                         authorized: bool = False, upstream_egress_acknowledged: bool = False):
    """Two independent arms, each stops on first failure; <=4 attempts per turn.

    Both arms use the same fixed JSON schema hints,120s Core deadline and three
    allowed reads. Only context presentation differs. Sequential order is fixed;
    server residency/cache/hardware are not controlled or attested by this lab.
    """
    manifest = preflight(directory=directory, endpoint=endpoint, model=model)
    if authorized is not True or upstream_egress_acknowledged is not True:
        raise ValueError("local_experiment_not_authorized")
    directory.mkdir(parents=True, exist_ok=False)
    _save(directory / "manifest.json", manifest)
    calls, snapshots, outcomes = [], [], []
    seed_digests = {}
    configuration = ComparisonConfig(model, timeout_seconds=120, evidence_mode="local_model")

    def execute(trial, *, candidate, arm):
        trial.directory.mkdir(parents=True, exist_ok=True)
        reports = {}
        for resource_id, text in trial.reports:
            reports[resource_id] = trial.directory / (resource_id + ".txt")
            reports[resource_id].write_text(text, encoding="utf-8")
        _, reader = _host_selection(
            reports=reports, endpoint=endpoint, model=model, session_id=SESSION,
            authorized=True, confirmed=True, reports_confirmed=True,
            upstream_egress_acknowledged=True, timeout_seconds=120, include_content=True,
        )

        class CountedPort:
            provider_id = _PROVIDER
            evidence_mode = "live"  # Actual HTTP, never independent model/weights evidence.

            def infer(self, request, *, cancellation=None):
                if len(calls) >= MAX_ATTEMPTS:
                    raise ValueError("local_experiment_budget_exhausted")
                entry = {
                    "attempt": len(calls) + 1, "arm": arm, "phase": trial.phase,
                    "timeout_ms": round(request.timeout_seconds * 1000),
                }
                calls.append(entry)
                _save(directory / "inferences.json", calls)
                diagnostics = _PhaseDiagnostics()
                result = None
                try:
                    payload = json.loads(request.messages[0].content)
                    history = payload.get("history", [])
                    if (payload["query"] != trial.query
                            or bool(history) is not trial.include_canonical_history):
                        raise ValueError("local_experiment_context_mismatch")
                    if trial.phase == "control" and PREFERENCE in json.dumps(payload):
                        entry["blocked_before_transport"] = True
                        raise ValueError("control_input_contains_preference")
                    entry.update(history_pairs=len(history),
                                 observations=len(payload["observations"]))
                    transport = LocalChatHttpTransport(
                        endpoint=endpoint, phase_observer=diagnostics.observer("transport"),
                    )
                    provider = ChatCompletionsInferenceProvider(
                        model=model, transport=transport, evidence_mode="live",
                        structured_tool_output=True, hermes_context=candidate,
                        phase_observer=diagnostics.observer("provider"),
                    )
                    result = provider.infer(request, cancellation=cancellation)
                    return result
                finally:
                    entry.update(status=result.status if result else "failed",
                                 error_code=(result.error_code if result
                                             else "inference_unavailable"),
                                 input_tokens=result.input_tokens if result else None,
                                 output_tokens=result.output_tokens if result else None,
                                 phase_diagnostics=diagnostics.snapshot())
                    _save(directory / "inferences.json", calls)

        guard = CampaignInferenceGuard(
            CountedPort, model=model, provider_id=_PROVIDER, evidence_mode="live",
            authorized=True, max_calls=4,
        )
        result = _run_report_loop(
            trial.query, reader=reader, port=guard, session_id=SESSION, model=model,
            timeout_seconds=120, include_content=True,
            core_factory=lambda: _isolated_core(trial.directory / "runtime"),
            redactor=ConsoleRuntime(output_format="json"), output_schema=OUTPUT_SCHEMA,
            expected_provider_id=_PROVIDER, expected_evidence_mode="live",
            include_canonical_history=trial.include_canonical_history,
        )
        result.update(account_used=False, real_model_verified=False, local_weights_verified=False)
        _save(trial.directory / "canonical-result.json", result)
        _save(trial.directory / "budget.json", guard.snapshot())
        return TurnExecution(result, guard.snapshot()["attempted_model_calls"])

    def readback(trial, result):
        runtime = trial.directory / "runtime"
        core = _isolated_core(runtime)
        rows = core.memory_service.repository.fetch_recent_turns(SESSION, 10)
        if (not rows or rows[-1].request_content != trial.query
                or any(row.user_id != "user://local_operator" for row in rows)):
            raise ValueError("local_experiment_readback_refused")
        row = rows[-1]
        events = core.observability_service.repository.list_events(
            session_id=SESSION, event_names=("memory_recorded",), limit=10,
        )
        matching = [event for event in events
                    if event.payload.get("conversation_readback", {}).get("record_timestamp")
                    == row.timestamp]
        if len(matching) != 1:
            raise ValueError("local_experiment_readback_refused")
        request_id = matching[0].request_id
        pack = export_conversation(
            memory_db=runtime / "memory.db", events_db=runtime / "events.db", session_id=SESSION,
            request_id=request_id, principal_ref="user://local_operator",
            authorized=True, include_content=True,
        )
        if pack.get("content_included") is not True or pack["query"] != trial.query:
            raise ValueError("local_experiment_readback_refused")
        current = core.observability_service.repository.list_events(
            session_id=SESSION, request_id=request_id, limit=200,
        )
        return CanonicalReadback(
            row.response_text, pack["response_text"],
            sum(event.event_name == "model_tool_loop_model_requested" for event in current),
            sum(event.event_name == "model_tool_loop_tool_observed" for event in current),
            sum(event.event_name == "operation_dispatched" for event in current),
        )

    def clone(source, target):
        target.mkdir(parents=True, exist_ok=False)
        (target / "runtime").mkdir()
        digests = []
        for name in ("memory.db", "events.db"):
            original = source / "runtime" / name
            if any(Path(str(original) + suffix).exists()
                   for suffix in ("-wal", "-shm", "-journal")):
                raise ValueError("non_quiescent_experiment_store")
            copied = target / "runtime" / name
            shutil.copy2(original, copied)
            digest = hashlib.sha256(original.read_bytes()).hexdigest()
            if hashlib.sha256(copied.read_bytes()).hexdigest() != digest:
                raise ValueError("local_experiment_snapshot_mismatch")
            digests.append(digest)
        arm = target.parent.name
        if arm in seed_digests and seed_digests[arm] != digests:
            raise ValueError("local_experiment_snapshot_mismatch")
        seed_digests[arm] = list(digests)
        snapshots.append({"arm": target.parent.name, "phase": target.name,
                          "database_sha256": digests})
        _save(directory / "snapshots.json", snapshots)

    for name, candidate in (("jarvis_structured", False), ("hermes_context", True)):
        outcome = run_conversation_arm(
            directory=directory / name, name=name, configuration=configuration,
            execute_turn=lambda trial, selected=candidate, arm=name: execute(
                trial, candidate=selected, arm=arm,
            ), readback_turn=readback, clone_seed=clone,
        )
        outcomes.append(outcome)
        _save(directory / (name + ".json"), outcome)
    result = {**manifest, "status": "recorded", "attempted_inferences": len(calls),
              "arms": outcomes, "comparison": compare_conversations(*outcomes),
              "model": model, "sequential_order": [arm["name"] for arm in outcomes],
              "residency_controlled": False, "generation_parameters_controlled": False,
              "context_window_verified": False, "improvement_claim": False}
    _save(directory / "comparison.json", result)
    return result


class _SafeParser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError("local_experiment_refused")


def main(argv=None):
    parser = _SafeParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--runtime-dir", required=True, type=Path)
    parser.add_argument("--endpoint", default=ENDPOINT)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--authorized-local", action="store_true")
    parser.add_argument("--acknowledge-upstream-egress", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = (run_local_experiment(
            directory=args.runtime_dir, endpoint=args.endpoint, model=args.model,
            authorized=args.authorized_local,
            upstream_egress_acknowledged=args.acknowledge_upstream_egress,
        ) if args.execute else preflight(
            directory=args.runtime_dir, endpoint=args.endpoint, model=args.model,
        ))
        print(json.dumps(result, ensure_ascii=True, allow_nan=False))
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"cancelled"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"local_experiment_refused"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
