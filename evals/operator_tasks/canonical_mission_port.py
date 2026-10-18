"""Evaluate exact canonical Core output in a disposable, host-selected runtime.

Projection may select the literal unverified analysis already in the final.
It never repairs an answer, supplies an oracle or grants effects to a model.
"""

from __future__ import annotations

import hashlib
import json
import math
import stat
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from threading import Event

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.conversation_export import export_conversation
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.reviewed_knowledge import GENERATIVE_ANALYSIS_MARKER
from shared.types import ChannelType, InputType, PermissionDecision, RequestId, SessionId

from .corpus import Source
from .runner import Binding, ExecutionRequest, ExecutionResult, _identifier

ensure_src_paths()

from orchestrator_service.service import OrchestratorService  # noqa: E402
from synthesis_engine.engine import SynthesisEngine  # noqa: E402

_MODES = {"fixture": "fixture", "injected_transport": "injected_transport", "live": "model_real"}


def _prompt(request):
    if (type(request) is not ExecutionRequest or type(request.binding) is not Binding
            or request.history is not None or type(request.sources) is not tuple
            or not 1 <= len(request.sources) <= 16
            or any(type(item) is not Source for item in request.sources)):
        raise ValueError("invalid_canonical_mission_request")
    for key in ("run_id", "request_id", "case_id", "revision", "subject_ref", "session_ref"):
        if not _identifier(getattr(request.binding, key)):
            raise ValueError("invalid_canonical_mission_request")
    value = (request.brief + "\nRequest binding: "
             + json.dumps(asdict(request.binding), sort_keys=True))
    value += "\nSupplied sources: " + json.dumps([asdict(item) for item in request.sources])
    if not value.strip() or len(value) > 16000:
        raise ValueError("invalid_canonical_mission_request")
    return value


class CanonicalMissionTaskPort:
    """Native Core remains sole owner of governance, final synthesis and memory."""

    def __init__(self, runtime_root: Path, *, authorized=False, inference_port=None, model=None,
                 provider_id="fixture", inference_evidence_mode="fixture", cancellation=None,
                 clock=time.monotonic, core_factory=_isolated_core):
        if (type(authorized) is not bool or not isinstance(runtime_root, Path)
                or not runtime_root.is_absolute() or not callable(clock)
                or not callable(core_factory) or (inference_port is None) != (model is None)
                or inference_evidence_mode not in _MODES
                or (cancellation is not None and not isinstance(cancellation, Event))):
            raise ValueError("invalid_canonical_mission_port")
        self.evidence_mode = _MODES[inference_evidence_mode] if inference_port else "core_local"
        self._root, self._authorized, self._factory = runtime_root, authorized, core_factory
        self._inference, self._model, self._provider = inference_port, model, provider_id
        self._inference_mode, self._cancellation = inference_evidence_mode, cancellation
        self._clock = clock
        self._turns = self._verified = 0
        self._clarifications = self._decision_required = 0
        self._last = None

    def __repr__(self):
        return "CanonicalMissionTaskPort(authority='assist_only', production_memory=False)"

    def snapshot(self):
        return {"core_turns": self._turns, "canonical_finals_verified": self._verified,
                "clarifications_required": self._clarifications,
                "native_decisions_required": self._decision_required,
                "last_outcome": self._last, "production_memory_opened": False,
                "answer_repair": False, "operation_authority": False,
                "projection": "canonical_unverified_analysis" if self._inference
                else "canonical_full_text"}

    def execute(self, request):
        if self._authorized is not True:
            raise ValueError("canonical_mission_opt_in_required")
        text = _prompt(request)
        binding = request.binding
        now = self._clock()
        if (type(request.deadline) not in {int, float} or not math.isfinite(request.deadline)
                or type(now) not in {int, float} or not math.isfinite(now)
                or not now < request.deadline <= now + 120
                or (self._cancellation and self._cancellation.is_set())):
            raise ValueError("invalid_canonical_mission_deadline")
        # Only a fresh private test directory, never the user's canonical runtime.
        for path in (self._root, *self._root.parents):
            info = path.lstat()
            if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400):
                raise ValueError("canonical_mission_runtime_refused")
        if self._root.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError("canonical_mission_runtime_refused")
        token = hashlib.sha256(json.dumps(asdict(binding), sort_keys=True).encode()).hexdigest()
        runtime = self._root / ("case-" + token)
        runtime.mkdir(mode=0o700)
        core = self._factory(runtime)
        if not isinstance(core, OrchestratorService) or core.model_tool_loop is not None:
            raise ValueError("invalid_canonical_mission_core")
        if self._inference is not None:
            core.synthesis_engine = SynthesisEngine(
                generative_port=self._inference, generative_model=self._model,
                generative_provider_id=self._provider,
                generative_evidence_mode=self._inference_mode,
                generative_timeout_seconds=min(120, request.deadline - self._clock()),
                generative_cancellation=self._cancellation,
            )
        elif (core.synthesis_engine._generative_port is not None
              or core.synthesis_engine._inference_port is not None):
            raise ValueError("invalid_canonical_mission_core")
        contract = InputContract(
            request_id=RequestId(binding.request_id), session_id=SessionId(binding.session_ref),
            channel=ChannelType.CONSOLE, input_type=InputType.TEXT, content=text,
            timestamp=datetime.now(UTC).isoformat(), user_id=f"user://{binding.subject_ref}",
            canonical_user_ref=f"user://{binding.subject_ref}",
            operator_identity_ref=f"operator://{binding.subject_ref}",
            surface_id="surface://mission-evaluation", surface_kind="console",
            surface_session_id=binding.session_ref, surface_capability_scope=[],
            requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
        )
        directive = core.executive_engine.direct(contract)
        self._clarifications += int(directive.requires_clarification is True)
        if (directive.should_execute_operation
                or directive.intent not in {"analysis", "conversation", "general_assistance"}):
            self._last = "core_scope_refused"
            return ExecutionResult(binding, "needs_decision")
        before_dispatch = self._clock()
        if (type(before_dispatch) not in {int, float}
                or not math.isfinite(before_dispatch)
                or not now <= before_dispatch < request.deadline
                or (self._cancellation and self._cancellation.is_set())):
            self._last = "stopped_before_core_dispatch"
            return ExecutionResult(binding, "incomplete")
        try:
            response = core.handle_input(contract)
            self._turns += 1
            if (response.request_id != binding.request_id
                    or response.session_id != binding.session_ref
                    or any(getattr(response, key, False) is not None for key in (
                        "operation_dispatch", "operation_result", "adapter_grant",
                        "adapter_grant_claim", "action_confirmation_claim",
                        "action_confirmation_challenge", "adapter_action_intent",
                    ))):
                raise ValueError("canonical_mission_result_refused")
            if response.governance_decision.decision != PermissionDecision.ALLOW:
                self._decision_required += 1
                self._last = "native_decision_required"
                return ExecutionResult(binding, "needs_decision")
            exported = export_conversation(
                memory_db=runtime / "memory.db", events_db=runtime / "events.db",
                session_id=binding.session_ref, request_id=binding.request_id,
                principal_ref=f"user://{binding.subject_ref}",
                authorized=True, include_content=True, cancellation=self._cancellation,
            )
            if (not exported["content_included"] or exported["query"] != text
                    or exported["response_text"] != response.response_text
                    or exported["governance_decision"]
                    != response.governance_decision.decision.value):
                raise ValueError("canonical_mission_result_refused")
            self._verified += 1
            candidate = exported["response_text"]
            if self._inference is not None:
                if exported["generative_status"] != "accepted":
                    self._last = "generative_not_accepted"
                    return ExecutionResult(binding, "incomplete")
                if candidate.count(GENERATIVE_ANALYSIS_MARKER) != 1:
                    raise ValueError("canonical_mission_projection_refused")
                section = candidate.split(GENERATIVE_ANALYSIS_MARKER, 1)[1]
                lines = [line[10:] for line in section.splitlines()
                         if line.startswith("Analysis: ")]
                if len(lines) != 1:
                    raise ValueError("canonical_mission_projection_refused")
                candidate = json.loads(lines[0])
                if (type(candidate) is not str or len(candidate) > 4000
                        or len(candidate) != exported["generative_analysis_characters"]):
                    raise ValueError("canonical_mission_projection_refused")
            finished = self._clock()
            if (type(finished) not in {int, float} or not now <= finished < request.deadline
                    or (self._cancellation and self._cancellation.is_set())):
                raise ValueError("canonical_mission_deadline_exceeded")
            self._last = "canonical_product_submitted_for_grading"
            return ExecutionResult(binding, "completed", candidate.encode("utf-8"))
        except KeyboardInterrupt:
            self._last = "canonical_mission_interrupted"
            raise
        except Exception:
            self._last = "canonical_mission_unconfirmed"
        return ExecutionResult(binding, "error")
