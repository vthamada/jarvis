"""Actual CLI products over supplied content; not model or host-effect evidence."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from operational_service.adapters.code_sandbox.patch_review import PatchReviewer, text_sha256

from apps.jarvis_console import cli

ROOT = Path(__file__).resolve().parents[2]


def code_document(text="value = 'café'\n", replacement="chá"):
    original = "café"
    start = text.index(original)
    snapshot = PatchReviewer(("src/notes.py",)).snapshot({"src/notes.py": text})
    return {
        "schema_version": "jarvis-code-review-input-v1", "files": {"src/notes.py": text},
        "proposal": {
            "expected_snapshot_sha256": snapshot.sha256,
            "files": [{"path": "src/notes.py", "expected_sha256": text_sha256(text),
                       "edits": [{"start": start, "end": start + len(original),
                                  "expected_text": original, "replacement": replacement}]}],
        },
    }


def research_document(text="O café está previsto para quinta-feira. O orçamento é 50."):
    return {
        "schema_version": "jarvis-research-input-v1", "query": "café quinta-feira",
        "as_of": "2026-10-05T12:00:00Z",
        "sources": [{"source_ref": "provided:notes-v1", "text": text,
                     "observed_at": "2026-10-04T12:00:00Z", "expires_at": None}],
    }


def invoke(command, document, tmp_path, *, content=False, output_format="json", extra=()):
    args = [sys.executable, "-m", "apps.jarvis_console", "--format", output_format, command]
    if content:
        args.append("--include-content")
    args.extend(extra)
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE="1",
               DATABASE_URL="postgresql://not-used.invalid/blocked")
    data = (document if type(document) is bytes else
            json.dumps(document, ensure_ascii=False).encode("utf-8"))
    # Covers complete console module startup under Windows/OneDrive host load,
    # not a runtime deadline or relaxation of any review/input guard.
    return subprocess.run(args, input=data, capture_output=True, cwd=tmp_path, env=env, timeout=60)


def product(completed, output_format="json"):
    assert completed.returncode == 0, completed.stderr.decode()
    assert not completed.stderr
    output = completed.stdout.decode()
    if output_format == "json":
        envelope = json.loads(output)
        assert envelope["command_id"] in {"code-review", "research-review"}
        assert envelope["redacted"] is False
        assert len(envelope["outputs"]) == 1
        return json.loads(envelope["outputs"][0])
    return json.loads(output)


@pytest.mark.parametrize("command,document", [
    ("code-review", code_document()), ("research-review", research_document()),
], ids=["code", "research"])
def test_real_subprocess_standalone_defaults_private_no_writes(tmp_path, command, document):
    sentinel = tmp_path / "human-file.txt"
    sentinel.write_text("preserve exact human content", encoding="utf-8")
    inventory = sorted(p.name for p in tmp_path.iterdir())
    before = sentinel.read_bytes()
    completed = invoke(command, document, tmp_path)
    payload = product(completed)
    assert payload["read_only"] is True
    assert payload["requires_human_review"] is True
    assert payload["draft"] is True
    assert payload["content_withheld"] is False
    assert b"caf" not in completed.stdout
    assert b"src/notes.py" not in completed.stdout
    assert b"provided:notes-v1" not in completed.stdout
    assert sorted(p.name for p in tmp_path.iterdir()) == inventory
    assert sentinel.read_bytes() == before


@pytest.mark.parametrize("format", ["text", "json"])
def test_real_code_diff_exposes_exact_candidate_without_effect(tmp_path, format):
    payload = product(invoke("code-review", code_document(), tmp_path, content=True,
                             output_format=format), format)
    assert "-value = 'café'" in payload["content"]["diff"]
    assert "+value = 'chá'" in payload["content"]["diff"]
    assert payload["telemetry"]["status"] == "reviewable"
    assert payload["telemetry"]["authority_granted"] is False
    assert payload["telemetry"]["tests_executed"] is False
    assert payload["telemetry"]["host_effects"] is False
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("format", ["text", "json"])
def test_real_research_quote_has_exact_unicode_span_and_declared_unknown(tmp_path, format):
    document = research_document()
    payload = product(invoke("research-review", document, tmp_path, content=True,
                             output_format=format), format)
    quote = payload["review_candidates"][0]
    start, end = quote["span"]["start"], quote["span"]["end"]
    assert document["sources"][0]["text"][start:end] == quote["quote"]
    assert quote["text_sha256"] == text_sha256(document["sources"][0]["text"])
    assert "café" in quote["quote"]
    assert quote["currentness"] == payload["currentness"] == "unknown"
    assert quote["untrusted_evidence"] is True
    assert payload["authority"] == "none"
    assert payload["truth_assessment"] == payload["conflict_assessment"] == "not_assessed"


@pytest.mark.parametrize("command,document", [
    ("code-review", code_document("value = 'café' # password=private-marker\n")),
    ("research-review", research_document("café password=private-marker.")),
], ids=["code", "research"])
def test_real_secret_content_withheld_without_mangling_json_hashes(tmp_path, command, document):
    completed = invoke(command, document, tmp_path, content=True)
    payload = product(completed)
    assert payload["content_withheld"] is True
    assert payload["content_withheld_reason"] == "sensitive_display_content"
    assert "content" not in payload and "review_candidates" not in payload
    assert b"private-marker" not in completed.stdout and b"<redacted>" not in completed.stdout


@pytest.mark.parametrize("command", ["code-review", "research-review"])
@pytest.mark.parametrize("raw", [
    b'{"private-marker":', b'{"x":1,"x":2}', b'{"x":NaN}', b'[]',
    b'{"nested":{"x":1,"x":2}}', b'{"bad":"\xff"}', b' ' * 65537,
], ids=["syntax", "duplicate", "nonfinite", "array", "nestedduplicate", "utf8", "oversize"])
def test_real_invalid_stdin_is_fixed_error_without_partial_output(tmp_path, command, raw):
    result = invoke(command, raw, tmp_path)
    assert result.returncode == 2
    assert not result.stdout
    error = json.loads(result.stderr)
    assert error["error_code"] == "review_input_refused"
    assert b"private-marker" not in result.stderr
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("command,document", [
    ("code-review", code_document()), ("research-review", research_document()),
], ids=["code", "research"])
def test_invalid_arguments_never_echo_private_marker(tmp_path, command, document):
    result = invoke(command, document, tmp_path, extra=["--private-marker"])
    assert result.returncode == 2
    assert not result.stdout
    assert json.loads(result.stderr)["error_code"] == "invalid_cli_usage"
    assert b"private-marker" not in result.stderr


@pytest.mark.parametrize("command,document", [
    ("code-review", code_document()), ("research-review", research_document()),
], ids=["code", "research"])
def test_main_dispatch_never_builds_core_or_uses_network(monkeypatch, capsys, command, document):
    import socket

    monkeypatch.setattr(cli.JarvisConsole, "build", lambda **k: pytest.fail("Core constructed"))
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("network fetch"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(document)))
    assert cli.main([command, "--format", "json", "--include-content"]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert json.loads(captured.out)["status"] == "success"


def test_real_wrong_patch_preimage_fails_no_diff(tmp_path):
    document = code_document()
    document["proposal"]["files"][0]["edits"][0]["expected_text"] = "private-marker"
    result = invoke("code-review", document, tmp_path, content=True)
    assert result.returncode == 2 and not result.stdout
    assert b"private-marker" not in result.stderr


def test_real_expired_source_never_enters_review_quotes(tmp_path):
    document = research_document()
    document["sources"][0]["expires_at"] = "2026-10-05T10:00:00Z"
    payload = product(invoke("research-review", document, tmp_path, content=True))
    assert payload["status"] == "no_eligible_evidence"
    assert payload["counts"]["withheld_sources"] == 1
    assert payload["review_candidates"] == []
