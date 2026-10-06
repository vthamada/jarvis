"""Opt-in canonical recall inspection using a disposable, real Core runtime.

Fixed public corpus only. This is trusted local composition, not authentication,
an open recall endpoint, a new retrieval policy or a capability promotion.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.jarvis_console.voice_pilot import _isolated_core
from shared.contracts import InputContract
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId

CORPUS_VERSION = "memory-recall-public-v1"
SUBJECT = "recall-pilot-alpha"
MISSION = "recall-pilot-rollout"


@dataclass(frozen=True)
class PilotContext:
    """Explicit trusted binding supplied by this composition, not by a model."""

    subject: str
    session: str
    mission: str | None = None

    def input(self, request_id: str, text: str) -> InputContract:
        return InputContract(
            request_id=RequestId(request_id),
            session_id=SessionId(self.session),
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=text,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mission_id=MissionId(self.mission) if self.mission else None,
            user_id=self.subject,
            surface_id="surface://isolated-memory-recall",
            surface_kind="console",
            surface_session_id=self.session,
            surface_capability_scope=[],
            operator_identity_ref=f"operator://{self.subject}",
            canonical_user_ref=f"user://{self.subject}",
            requested_autonomy_level="assist_only",
            max_autonomy_level="assist_only",
        )


class RecallPilotPort:
    """Inspect canonical selection; do not alter ranking, text or stored records."""

    def __init__(self, core, context: PilotContext):
        self.core = core
        self.context = context

    def _validate(self, contract: InputContract) -> None:
        expected = self.context.input("binding-only", "binding-only")
        fields = (
            "user_id",
            "canonical_user_ref",
            "operator_identity_ref",
            "session_id",
            "surface_id",
            "surface_kind",
            "surface_session_id",
            "mission_id",
            "surface_capability_scope",
            "requested_autonomy_level",
            "max_autonomy_level",
        )
        if not isinstance(contract, InputContract) or any(
            getattr(contract, name) != getattr(expected, name) for name in fields
        ):
            raise ValueError("recall_binding_drift")
        if contract.adapter_action_request is not None or contract.action_confirmation_receipt_id:
            raise ValueError("recall_effect_request_refused")
        if self.context.mission:
            state = self.core.memory_service.get_mission_state(self.context.mission)
            if state is not None and (
                str(state.mission_id) != self.context.mission
                or state.owner_context != self.context.subject
            ):
                raise ValueError("recall_mission_subject_mismatch")

    def inspect(self, contract: InputContract) -> dict[str, object]:
        self._validate(contract)
        recovered = self.core.memory_service.recover_for_input(contract)
        scope = recovered.user_scope_context
        permitted_refs = {f"memory://user/{self.context.subject}"}
        if self.context.mission:
            permitted_refs.add(f"memory://mission/{self.context.mission}")
        refs = list(scope.memory_refs) if scope else []
        if scope and (scope.user_id != self.context.subject or not set(refs) <= permitted_refs):
            raise ValueError("recall_user_ref_drift")
        candidates = []
        for candidate in recovered.semantic_memory_candidates:
            if (
                not self.context.mission
                or candidate.anchor_ref != f"memory://mission/{self.context.mission}/semantic"
                or not candidate.read_only
                or candidate.memory_write_allowed
            ):
                raise ValueError("recall_candidate_ref_drift")
            candidates.append(
                {
                    "anchor_ref": candidate.anchor_ref,
                    "source_kind": candidate.source_kind,
                    "observed_at": str(candidate.observed_at),
                    "freshness_status": candidate.freshness_status,
                    "relevance_reason": candidate.relevance_reason,
                    "evidence_ref_count": len(candidate.evidence_refs),
                }
            )
        sources = next(
            (
                item.partition("=")[2]
                for item in recovered.recovered_items
                if item.startswith("cross_session_recall_sources=")
            ),
            "none",
        )
        status = next(
            (
                item.partition("=")[2]
                for item in recovered.recovered_items
                if item.startswith("cross_session_recall_status=")
            ),
            "not_applicable",
        )
        return {
            "user_scope_status": scope.context_status if scope else "not_applicable",
            "prior_user_interaction_count": scope.interaction_count if scope else 0,
            "user_memory_refs": refs,
            "cross_session_recall_status": status,
            "canonical_sources": sources.split(";") if sources != "none" else [],
            "semantic_candidates": candidates,
            "prior_session_turn_count": len(
                self.core.memory_service.repository.fetch_recent_turns(self.context.session, 20)
            ),
            "explanation_mode": "canonical_policy_metadata_only",
        }

    def interact(self, contract: InputContract) -> dict[str, object]:
        before = self.inspect(contract)
        response = self.core.handle_input(contract)
        turns = self.core.memory_service.repository.fetch_recent_turns(self.context.session, 20)
        if (
            response.request_id != contract.request_id
            or response.session_id != contract.session_id
            or not response.memory_record.memory_record_id
            or not turns
            or turns[-1].request_content != contract.content
            or turns[-1].response_text != response.response_text
            or response.operation_dispatch is not None
            or response.operation_result is not None
        ):
            raise ValueError("recall_canonical_final_refused")
        events = [event for event in response.events if event.event_name == "memory_recovered"]
        if (
            len(events) != 1
            or events[0].payload.get("user_scope_interaction_count")
            != before["prior_user_interaction_count"]
        ):
            raise ValueError("recall_observation_mismatch")
        return {
            "selection_before_turn": before,
            "memory_record_id": str(response.memory_record.memory_record_id),
            "core_event_count": len(response.events),
            "governance_decision": response.governance_decision.decision.value,
            "governance_containment_hint": response.governance_decision.containment_hint,
            "continuity_action": response.deliberative_plan.continuity_action,
            "recall_outcome": (
                "canonical_context_selected"
                if before["semantic_candidates"]
                else "persisted_tracking_only"
            ),
            "useful_continuity_demonstrated": False,
            "final_matches_canonical_record": True,
            "operation_dispatched": False,
        }


def run_memory_recall_pilot(*, authorized: bool = False) -> dict[str, object]:
    if authorized is not True:
        raise ValueError("memory_recall_pilot_opt_in_required")
    base = Path(tempfile.gettempdir()).resolve()
    workspace = Path(__file__).resolve().parents[2]
    if base == workspace or base.is_relative_to(workspace):
        raise ValueError("memory_recall_temp_base_refused")
    with TemporaryDirectory(prefix="jarvis-memory-recall-pilot-", dir=str(base)) as runtime:
        core = _isolated_core(Path(runtime))
        first = PilotContext(SUBJECT, "recall-pilot-session-a", MISSION)
        second = PilotContext(SUBJECT, "recall-pilot-session-b", MISSION)
        other = PilotContext("recall-pilot-beta", "recall-pilot-session-c")
        cases = [
            ("seed", first, "Plan an internal pilot rollout with reversible checkpoints."),
            ("same_session", first, "Plan the next pilot checkpoint and preserve prior evidence."),
            (
                "new_session_same_subject",
                second,
                "Continue the internal pilot rollout from prior evidence.",
            ),
            ("new_subject", other, "Explain how to plan an internal pilot rollout."),
        ]
        results = {}
        for index, (name, context, text) in enumerate(cases):
            port = RecallPilotPort(core, context)
            results[name] = port.interact(context.input(f"recall-pilot-request-{index}", text))
        return {
            "pilot_mode": "isolated_memory_recall",
            "corpus_version": CORPUS_VERSION,
            "evidence_mode": "core_local",
            "runtime_mode": "temporary_sqlite",
            "core_turn_count": len(cases),
            "operator_authenticated": False,
            "runtime_capability_promoted": False,
            "open_recall_quality_measured": False,
            "retention_mutation_performed": False,
            "cases": results,
            "limitations": [
                "explicit_trusted_subject_and_mission_bindings",
                "canonical_metadata_recall_not_verbatim_episodic_search",
                "no_authentication_or_multiuser_endpoint",
                "no_open_response_quality_benchmark",
            ],
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args(argv)
    if not args.authorized:
        parser.error("memory_recall_pilot_opt_in_required")
    print(json.dumps(run_memory_recall_pilot(authorized=True), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
