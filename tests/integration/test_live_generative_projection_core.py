"""Actual sovereign Core renderer -> browser module, never a real account/model."""

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from apps.jarvis_api.analysis_service import AnalysisService
from apps.jarvis_api.contracts import SessionIdentity
from apps.jarvis_api.generative_profile import GenerativeProfile
from apps.jarvis_console.voice_pilot import _isolated_core
from shared.model_inference import InferenceResult

ROOT = Path(__file__).resolve().parents[2]
QUERY = "Compare os relatórios de documentação e observabilidade do piloto."
IDENTITY = SessionIdentity(
    "session://web-live/" + "1" * 32,
    "operator://web-live/" + "2" * 32,
    "user://web-live/" + "3" * 32,
)


def project(result):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable; no cross-language projection acceptance inferred")
    module = (ROOT / "apps/jarvis_web/live-generative-projection.mjs").as_uri()
    program = (
        "import { webcrypto } from 'node:crypto';"
        "if (!globalThis.crypto) globalThis.crypto = webcrypto;"
        f"const {{ projectGenerativeResult }} = await import({json.dumps(module)});"
        "process.stdin.setEncoding('utf8'); let input = '';"
        "for await (const part of process.stdin) input += part;"
        "const result = JSON.parse(input); const before = JSON.stringify(result);"
        "const projection = await projectGenerativeResult(result);"
        "console.log(JSON.stringify({projection, unchanged:before===JSON.stringify(result)}));"
    )
    completed = subprocess.run(
        [node, "--input-type=module", "-e", program],
        cwd=ROOT,
        input=json.dumps(result, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["unchanged"] is True
    return output["projection"]


@pytest.mark.parametrize("variant", ["empty", "unicode", "lines", "markup", "citations", "limits"])
def test_real_core_literal_projection_exact_canonical_restart(tmp_path, variant):
    candidate = {
        "analysis": "Compare os critérios declarados com a evidência observada.",
        "assumptions": [],
        "limitations": [],
        "citations": [],
    }
    if variant == "unicode":
        candidate.update(
            analysis='Documentação, ação e limites: 🚀; "dados" apenas.',
            assumptions=["Escopo comparável."],
            limitations=["Sem corpo real."],
        )
    elif variant == "lines":
        candidate.update(analysis="Primeira linha.\nSegunda linha.\tDados apenas.\rFim.")
    elif variant == "markup":
        candidate.update(analysis="<b>literal</b> [texto](a:b) & _*~# / `texto` !")
    elif variant == "limits":
        candidate.update(
            analysis="é" * 4000,
            assumptions=[str(i) + "x" * 255 for i in range(8)],
            limitations=["z" * 512],
        )

    class Port:
        provider_id, evidence_mode = "responses_plan", "injected_transport"
        calls = 0

        def infer(self, request, *, cancellation=None):
            self.calls += 1
            source = json.loads(request.messages[0].content)["sources"][0]
            if variant == "citations":
                candidate["citations"] = [
                    {
                        "source_ref": source["source_ref"],
                        "start": start,
                        "end": end,
                        "quote": source["text"][start:end],
                    }
                    for start, end in ((0, 7), (11, 20), (24, 36), (39, 54))
                ]
            return InferenceResult(
                request.request_id,
                request.model,
                self.provider_id,
                "completed",
                text=json.dumps(candidate, ensure_ascii=False),
                evidence_mode=self.evidence_mode,
            )

    port = Port()
    credential_dir = tmp_path / "unopened-credentials"
    profile = GenerativeProfile(
        authorized=True,
        model="synthetic-model",
        credential_dir=credential_dir,
        profile_ref="profile-" + "a" * 64,
        port_factory=lambda *_args: port,
    )
    service = AnalysisService(tmp_path / "owned-core", generative_profile=profile)
    try:
        ticket = service.issue_generative_ticket(IDENTITY, consent=True)["ticket"]
        service.submit_generative(IDENTITY, ticket, QUERY, consent=True)
        service._worker.join(20)
        assert not service._worker.is_alive()
        envelope = service.get_result(IDENTITY, ticket)
        assert envelope["status"] == "completed", envelope
        result = envelope["result"]
        assert result["generative_status"] == "accepted", result
        before = copy.deepcopy(result)
        projection = project(result)
        assert projection is not None and projection["analysis"] == candidate["analysis"]
        assert projection["assumptions"] == candidate["assumptions"]
        assert projection["limitations"] == candidate["limitations"]
        assert projection["evidenceMode"] == "injected_transport"
        assert projection["citations"] == [
            {
                "sourceRef": citation["source_ref"],
                "start": citation["start"],
                "end": citation["end"],
                "quote": citation["quote"],
            }
            for citation in candidate["citations"]
        ]
        assert result == before
        restarted = _isolated_core(service.runtime_dir)
        turns = restarted.memory_service.repository.fetch_recent_turns(IDENTITY.session_ref, 10)
        assert len(turns) == 1
        assert turns[0].response_text.encode() == result["response_text"].encode()
        events = restarted.observability_service.repository.list_events(
            request_id=ticket, event_names=("response_synthesized",), limit=10
        )
        assert len(events) == 1 and events[0].payload["generative_status"] == "accepted"
        assert port.calls == 1 and not credential_dir.exists()
    finally:
        service.close()


def test_projection_asset_exact_allowlist_and_fixture_unchanged():
    from apps.jarvis_api.local_server import ASSETS, CSP
    from apps.jarvis_web.serve import ASSETS as fixture_assets

    assert ASSETS["/live-generative-projection.mjs"] == (
        "live-generative-projection.mjs",
        "text/javascript; charset=utf-8",
    )
    assert "/live-generative-projection.mjs" not in fixture_assets
    assert "script-src 'self'" in CSP and "connect-src 'self'" in CSP


def test_projection_asset_actual_loopback_http_and_no_cors():
    import http.client
    import threading

    from apps.jarvis_api.local_server import create_server

    server = create_server(object(), 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request("GET", "/live-generative-projection.mjs")
        response = connection.getresponse()
        body = response.read()
        assert response.status == 200
        assert response.getheader("Content-Type") == "text/javascript; charset=utf-8"
        assert response.getheader("Cache-Control") == "no-store"
        assert response.getheader("Access-Control-Allow-Origin") is None
        assert "script-src 'self'" in response.getheader("Content-Security-Policy")
        assert body == (ROOT / "apps/jarvis_web/live-generative-projection.mjs").read_bytes()
    finally:
        connection.close()
        server.auth.close()
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()
