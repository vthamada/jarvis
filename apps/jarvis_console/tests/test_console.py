from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from apps.jarvis_console.cli import JarvisConsole, build_parser, render_response, run_chat_command


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_console_ask_returns_orchestrated_response() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-ask"))
    response = console.ask(
        "Plan the controlled rollout.",
        session_id="sess-console",
        mission_id="mission-console",
    )
    rendered = render_response(response, debug=True)

    assert response.intent == "planning"
    assert "Leitura do objetivo" in response.response_text
    assert "request_id=" in rendered
    assert "decision=" in rendered


def test_console_chat_keeps_session_continuity() -> None:
    console = JarvisConsole.build(runtime_dir=runtime_dir("console-chat"))
    parser = build_parser()
    args = parser.parse_args(
        [
            "chat",
            "--session-id",
            "sess-console-chat",
            "--mission-id",
            "mission-console-chat",
            "--message",
            "Plan the final validation window.",
            "--message",
            "Analyze the previous plan.",
        ]
    )

    outputs = run_chat_command(console, args)

    assert len(outputs) == 2
    assert "Leitura do objetivo" in outputs[0]
    assert "Julgamento" in outputs[1]
    assert "continuidade ativa" in outputs[1].lower()
