"""Explicit browser proof: real Core, synthetic injected analysis, no account/network model.

This is a test harness, never a production profile or model-quality acceptance.
Only send synthetic/public inputs. Fresh runtime is preserved after shutdown.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "invalid_fixture_options\n")


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    args = parser.parse_args(argv)
    if not args.authorized:
        print("fixture_authorization_required", file=sys.stderr)
        return 2
    from apps.jarvis_api.__main__ import create_owned_runtime
    from apps.jarvis_api.analysis_service import AnalysisService
    from apps.jarvis_api.generative_profile import GenerativeProfile
    from apps.jarvis_api.local_server import create_server
    from shared.model_inference import InferenceResult

    class Port:
        provider_id = "responses_plan"
        evidence_mode = "injected_transport"

        def infer(self, request, *, cancellation=None):
            source = json.loads(request.messages[0].content)["sources"][0]
            candidate = {
                "analysis": "Compare o comportamento esperado com as evidências observadas. "
                "Nenhum relatório real foi fornecido; esta análise é uma fixture de teste.",
                "assumptions": ["A pergunta usa somente material sintético e público."],
                "limitations": ["Transporte sintético injetado, sem modelo real."],
                "citations": [
                    {
                        "source_ref": source["source_ref"],
                        "start": 0,
                        "end": min(7, len(source["text"])),
                        "quote": source["text"][:7],
                    }
                ],
            }
            return InferenceResult(
                request.request_id,
                request.model,
                self.provider_id,
                "completed",
                text=json.dumps(candidate),
                evidence_mode=self.evidence_mode,
            )

    runtime = create_owned_runtime()
    profile = GenerativeProfile(
        authorized=True,
        model="synthetic-model",
        credential_dir=runtime / "never-opened-credentials",
        profile_ref="profile-" + "a" * 64,
        port_factory=lambda *_args: Port(),
    )
    service = AnalysisService(runtime, generative_profile=profile)
    server = create_server(service, 0)
    try:
        print(f"TEST ONLY: http://127.0.0.1:{server.server_port}/", flush=True)
        print(f"Pairing code (one use, 120s): {server.auth.pairing_secret}", flush=True)
        print(f"Retained owned runtime: .jarvis_runtime/web-live/{runtime.name}", flush=True)
        print("Injected test transport only; no real model or account evidence.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.auth.close()
        service.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
