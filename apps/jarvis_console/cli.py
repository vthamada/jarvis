# ruff: noqa: E402
"""Minimal console surface for the JARVIS v1 baseline."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths

ensure_src_paths()

from memory_service.service import MemoryService
from observability_service.service import ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorResponse, OrchestratorService

from shared.contracts import InputContract
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId


@dataclass
class JarvisConsole:
    orchestrator: OrchestratorService

    @classmethod
    def build(
        cls,
        *,
        runtime_dir: Path | None = None,
        database_url: str | None = None,
    ) -> "JarvisConsole":
        if runtime_dir is None:
            return cls(orchestrator=OrchestratorService())
        runtime_dir.mkdir(parents=True, exist_ok=True)
        default_database_url = f"sqlite:///{(runtime_dir / 'memory.db').as_posix()}"
        resolved_database_url = database_url or default_database_url
        return cls(
            orchestrator=OrchestratorService(
                memory_service=MemoryService(database_url=resolved_database_url),
                operational_service=OperationalService(
                    artifact_dir=str(runtime_dir / "artifacts")
                ),
                observability_service=ObservabilityService(
                    database_path=str(runtime_dir / "observability.db")
                ),
            )
        )

    def ask(
        self,
        prompt: str,
        *,
        session_id: str,
        mission_id: str | None,
    ) -> OrchestratorResponse:
        contract = InputContract(
            request_id=RequestId(f"req-console-{uuid4().hex[:8]}"),
            session_id=SessionId(session_id),
            mission_id=MissionId(mission_id) if mission_id else None,
            channel=ChannelType.CHAT,
            input_type=InputType.TEXT,
            content=prompt,
            timestamp=datetime.now(UTC).isoformat(),
        )
        return self.orchestrator.handle_input(contract)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run the minimal JARVIS console.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Execute a single prompt.")
    ask_parser.add_argument("prompt", help="Single prompt to send to JARVIS.")
    ask_parser.add_argument("--session-id", default="console-ask")
    ask_parser.add_argument("--mission-id")
    ask_parser.add_argument("--debug", action="store_true")

    chat_parser = subparsers.add_parser("chat", help="Run a simple multi-turn chat session.")
    chat_parser.add_argument("--session-id", default=f"console-chat-{uuid4().hex[:6]}")
    chat_parser.add_argument("--mission-id")
    chat_parser.add_argument("--message", action="append", default=[])
    chat_parser.add_argument("--debug", action="store_true")

    return parser


def render_response(response: OrchestratorResponse, *, debug: bool) -> str:
    lines = [response.response_text]
    if debug:
        lines.extend(
            [
                f"request_id={response.request_id}",
                f"decision={response.governance_decision.decision.value}",
                f"continuity={response.deliberative_plan.continuity_action or 'none'}",
            ]
        )
    return "\n".join(lines)


def run_ask_command(console: JarvisConsole, args: Namespace) -> list[str]:
    response = console.ask(
        args.prompt,
        session_id=args.session_id,
        mission_id=args.mission_id,
    )
    return [render_response(response, debug=args.debug)]


def run_chat_command(console: JarvisConsole, args: Namespace) -> list[str]:
    outputs: list[str] = []
    if args.message:
        for message in args.message:
            response = console.ask(
                message,
                session_id=args.session_id,
                mission_id=args.mission_id,
            )
            outputs.append(render_response(response, debug=args.debug))
        return outputs

    print("JARVIS console ready. Type 'exit' to quit.")
    while True:
        prompt = input("jarvis> ").strip()
        if prompt.lower() in {"exit", "quit"}:
            break
        if not prompt:
            continue
        response = console.ask(
            prompt,
            session_id=args.session_id,
            mission_id=args.mission_id,
        )
        rendered = render_response(response, debug=args.debug)
        outputs.append(rendered)
        print(rendered)
    return outputs


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = JarvisConsole.build(runtime_dir=ROOT / ".jarvis_runtime" / "console")
    outputs = (
        run_ask_command(console, args)
        if args.command == "ask"
        else run_chat_command(console, args)
    )
    if args.command == "ask":
        print(outputs[0])
    elif args.message:
        for item in outputs:
            print(item)
    return 0
