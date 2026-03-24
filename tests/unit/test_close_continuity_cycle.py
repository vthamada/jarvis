from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from observability_service.service import ObservabilityService

from shared.events import InternalEventEnvelope
from tools.close_continuity_cycle import build_payload, render_markdown


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_close_continuity_cycle_builds_v1_5_cut() -> None:
    temp_dir = runtime_dir("cycle-closure")
    observability_db = temp_dir / "observability.db"
    evolution_db = temp_dir / "evolution.db"
    service = ObservabilityService(database_path=str(observability_db))
    service.ingest_events(
        [
            InternalEventEnvelope(
                event_id="evt-1",
                event_name="input_received",
                timestamp="2026-03-22T00:00:00+00:00",
                source_service="orchestrator-service",
                payload={"content": "continue"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-2",
                event_name="memory_recovered",
                timestamp="2026-03-22T00:00:01+00:00",
                source_service="orchestrator-service",
                payload={"continuity_recommendation": "retomar_missao_relacionada"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-3",
                event_name="intent_classified",
                timestamp="2026-03-22T00:00:02+00:00",
                source_service="orchestrator-service",
                payload={"intent": "analysis"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-4",
                event_name="context_composed",
                timestamp="2026-03-22T00:00:03+00:00",
                source_service="orchestrator-service",
                payload={"active_minds": ["mente_analitica"]},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-5",
                event_name="plan_built",
                timestamp="2026-03-22T00:00:04+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "retomar", "continuity_source": "related_mission"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-6",
                event_name="continuity_decided",
                timestamp="2026-03-22T00:00:05+00:00",
                source_service="orchestrator-service",
                payload={
                    "continuity_action": "retomar",
                    "continuity_source": "related_mission",
                    "continuity_target_mission_id": "mission-a",
                    "continuity_target_goal": "Analyze rollout risks.",
                },
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-7",
                event_name="governance_checked",
                timestamp="2026-03-22T00:00:06+00:00",
                source_service="orchestrator-service",
                payload={"decision": "allow_with_conditions"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-8",
                event_name="response_synthesized",
                timestamp="2026-03-22T00:00:07+00:00",
                source_service="orchestrator-service",
                payload={"continuity_action": "retomar"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
            InternalEventEnvelope(
                event_id="evt-9",
                event_name="memory_recorded",
                timestamp="2026-03-22T00:00:08+00:00",
                source_service="orchestrator-service",
                payload={"continuity_mode": "retomar"},
                request_id="req-cycle",
                session_id="sess-cycle",
                correlation_id="req-cycle",
            ),
        ]
    )

    payload = build_payload(
        observability_db=str(observability_db),
        evolution_db=str(evolution_db),
        limit=10,
    )

    assert payload["decision"] == "promote_to_v1_5"
    assert payload["evidence_summary"]["requests_audited"] == 1
    assert payload["evidence_summary"]["continuity_traces_healthy"] == 1
    assert payload["v1_5_scope"][0]["item_id"] == "v15-runtime-checkpoints"
    assert payload["v2_scope"][0]["item_id"] == "v2-specialists"


def test_close_continuity_cycle_renders_markdown() -> None:
    payload = {
        "cycle_id": "post-v1-cycle-1",
        "decision": "promote_to_v1_5",
        "evidence_summary": {
            "requests_audited": 2,
            "healthy_requests": 1,
            "incomplete_requests": 1,
            "attention_required_requests": 0,
            "continuity_traces_healthy": 1,
            "continuity_traces_incomplete": 1,
            "continuity_traces_attention_required": 0,
            "recent_evolution_proposals": 1,
            "recent_evolution_decisions": 1,
        },
        "v1_5_scope": [
            {
                "item_id": "v15-runtime-checkpoints",
                "title": "checkpoint e replay governados da continuidade",
                "target_phase": "v1.5",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "v2_scope": [
            {
                "item_id": "v2-specialists",
                "title": "especialistas subordinados maduros por dominio",
                "target_phase": "v2",
                "rationale": "racional",
                "dependency": "dependencia",
            }
        ],
        "decision_rationale": "decisao racional",
    }

    rendered = render_markdown(payload)

    assert "# Fechamento do Ciclo Pós-v1" in rendered
    assert "`v15-runtime-checkpoints`" in rendered
    assert "`v2-specialists`" in rendered
    assert "decisao racional" in rendered
