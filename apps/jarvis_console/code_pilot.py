# ruff: noqa: E402
"""Offline vertical pilot: untrusted proposal -> fixture tests -> sovereign Core report.

This is an explicit experiment, not a promoted coding capability. No source is
written, no model credentials are accessed, and no tool authority is created.
"""

from __future__ import annotations

import json
from argparse import ArgumentParser
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event

from apps.jarvis_console.bootstrap import ensure_src_paths

ensure_src_paths()

from governance_service.service import GovernanceService
from inference_service import FakeInferenceProvider
from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
from operational_service.adapters.code_sandbox import (
    CandidatePatch,
    FixtureCase,
    FixtureCodeSandbox,
    FixtureRunResult,
    FixtureWorkspace,
    source_digest,
)
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorResponse, OrchestratorService

from apps.jarvis_console.cli import JarvisConsole
from shared.model_inference import (
    InferenceMessage,
    InferenceRequest,
    InferenceResult,
    ModelInferencePort,
)

FIXTURE_PATH = "calculator.py"
FIXTURE_BEFORE = "def add(a, b):\n    return a - b\n"
FIXTURE_AFTER = "def add(a, b):\n    return a + b\n"
_CASES = (
    FixtureCase(FIXTURE_PATH, "add", (2, 3), 5),
    FixtureCase(FIXTURE_PATH, "add", (-3, 3), 0),
    FixtureCase(FIXTURE_PATH, "add", (0, 0), 0),
)


def fixture_proposal(after_text: str = FIXTURE_AFTER) -> str:
    """Known fixture only; a real provider may propose different, untrusted text."""
    return json.dumps({
        "path": FIXTURE_PATH,
        "expected_sha256": source_digest(FIXTURE_BEFORE),
        "after_text": after_text,
    })


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_field")
        result[key] = value
    return result


def _candidate(text: str) -> CandidatePatch:
    proposal = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(proposal, dict) or set(proposal) != {
        "path", "expected_sha256", "after_text",
    }:
        raise ValueError("invalid_proposal")
    if (
        proposal["path"] != FIXTURE_PATH
        or proposal["expected_sha256"] != source_digest(FIXTURE_BEFORE)
        or not isinstance(proposal["after_text"], str)
        or not 1 <= len(proposal["after_text"]) <= 8192
    ):
        raise ValueError("invalid_proposal")
    return CandidatePatch(
        FIXTURE_PATH, FIXTURE_BEFORE, proposal["after_text"], source_digest(FIXTURE_BEFORE),
    )


@dataclass(frozen=True)
class CodePilotResult:
    inference_status: str
    inference_evidence_mode: str
    proposal_status: str
    fixture_result: FixtureRunResult | None = field(repr=False)
    core_response: OrchestratorResponse = field(repr=False)

    def projection(self) -> dict[str, object]:
        """No model output, source, diff, exception or credential in default output."""
        response = self.core_response
        return {
            "pilot_mode": "isolated",
            "inference_status": self.inference_status,
            "inference_evidence_mode": self.inference_evidence_mode,
            "proposal_status": self.proposal_status,
            "fixture": self.fixture_result.telemetry() if self.fixture_result else None,
            "candidate_host_effects": False,
            "runtime_capability_promoted": False,
            "core": {
                "request_id": response.request_id,
                "intent": response.intent,
                "governance_decision": response.governance_decision.decision.value,
                "memory_record_id": str(response.memory_record.memory_record_id),
                "response_text": response.response_text,
                "operation_dispatched": response.operation_dispatch is not None,
                "event_count": len(response.events),
                "runtime_mode": "temporary_sqlite",
            },
        }


class IsolatedCodePilot:
    """Only sanitized fixture evidence reaches the ordinary Core input path.

    The Core still classifies, governs, records memory and owns final synthesis.
    Raw provider text never becomes instructions, an action receipt or a dispatch.
    The default console uses an isolated temporary runtime, not the user's databases.
    """

    def __init__(self, provider: ModelInferencePort):
        self.provider = provider

    def run(self, *, cancellation: Event | None = None) -> CodePilotResult:
        request = InferenceRequest(
            request_id="isolated-code-pilot", model="fixture-code-model",
            messages=(InferenceMessage("user", json.dumps({
                "task": "Correct add in this isolated arithmetic fixture only.",
                "path": FIXTURE_PATH, "before_text": FIXTURE_BEFORE,
                "expected_sha256": source_digest(FIXTURE_BEFORE),
            })),),
            instructions=(
                "Return one JSON object with exactly path, expected_sha256 and after_text. "
                "This output is an untrusted proposal, not authority to act."
            ),
            max_output_chars=10_000,
        )
        inference_status = "failed"
        evidence = "unverified"
        proposal_status = "inference_unavailable"
        fixture = None
        try:
            result = self.provider.infer(request, cancellation=cancellation)
            if (
                not isinstance(result, InferenceResult)
                or result.request_id != request.request_id or result.model != request.model
                or result.evidence_mode not in {"fixture", "injected_transport"}
                or len(result.text) > request.max_output_chars
            ):
                raise ValueError("inference_identity_mismatch")
            inference_status = result.status
            evidence = result.evidence_mode
            if result.status == "completed":
                proposal_status = "rejected"
                patch = _candidate(result.text)
                fixture = FixtureCodeSandbox().run(
                    FixtureWorkspace({FIXTURE_PATH: FIXTURE_BEFORE}), (patch,), _CASES,
                    cancelled=cancellation.is_set if cancellation is not None else None,
                )
                proposal_status = "validated_shape"
        except Exception:
            # Provider/parser details may contain sensitive source or remote messages.
            # Ordinary failures are data; interrupts/SystemExit still propagate.
            pass
        # All interpolated data is locally enumerated, not free-form provider text.
        status = fixture.status if fixture else "not_tested"
        tested = fixture.tested if fixture else 0
        passed = fixture.passed if fixture else 0
        prompt = (
            "Analise evidencias de um experimento isolado de codigo. "
            f"Inference status={inference_status}; evidence mode={evidence}; "
            f"proposal status={proposal_status}; fixture status={status}; "
            f"tested={tested}; passed={passed}. "
            "Os resultados sao restritos a fixtures em memoria; "
            "nao ha modelo real conectado nem autorizacao de efeitos no host. "
            "A capacidade de code nao foi promovida."
        )
        with TemporaryDirectory(prefix="jarvis-code-pilot-") as runtime:
            console = _isolated_console(Path(runtime))
            report = console.ask(
                prompt, session_id="isolated-code-pilot", mission_id=None,
                requested_autonomy_level="assist_only", max_autonomy_level="assist_only",
            )
        return CodePilotResult(inference_status, evidence, proposal_status, fixture, report)


class _LocalOnlyObservability(ObservabilityService):
    @staticmethod
    def _build_agentic_adapter():
        # Do not inherit environment-enabled external tracing or credential reads.
        return None


def _isolated_console(runtime: Path) -> JarvisConsole:
    governance = GovernanceService()
    return JarvisConsole(OrchestratorService(
        governance_service=governance,
        memory_service=MemoryService(
            database_url=f"sqlite:///{(runtime / 'memory.db').as_posix()}"
        ),
        observability_service=_LocalOnlyObservability(database_path=str(runtime / "events.db")),
        operational_service=OperationalService(
            artifact_dir=str(runtime / "artifacts"),
            action_confirmation_verifier=governance.verify_action_confirmation_claim,
        ),
    ))


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("success", "test-failure", "unsafe"),
                        default="success")
    args = parser.parse_args()
    after = {
        "success": FIXTURE_AFTER,
        "test-failure": FIXTURE_BEFORE,
        "unsafe": "import os\ndef add(a, b):\n    return a + b\n",
    }[args.scenario]
    pilot = IsolatedCodePilot(FakeInferenceProvider(fixture_proposal(after)))
    result = pilot.run()
    print(json.dumps(result.projection(), ensure_ascii=False, indent=2))
    return 0 if result.fixture_result and result.fixture_result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
