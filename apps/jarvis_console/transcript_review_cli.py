"""Explicit stdin-only transcript handoff to the sovereign, trusted local Core.

A downloaded review envelope is untrusted text, not authentication, voice
identity, an action receipt or proof that an ASR model ran. Its revision is a
declaration only. The trusted local caller must opt in afresh for each turn.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import sys
import tempfile
from pathlib import Path

from apps.jarvis_console.bootstrap import ROOT
from apps.jarvis_console.registry import CommandExecutionResult
from apps.jarvis_console.review_input import _requires_redaction
from apps.jarvis_console.runtime import ConsoleCommandError, ConsoleExitCode, ConsoleRuntime

MAX_ENVELOPE_BYTES = 131_072
MAX_DOCUMENT_BYTES = 32_768
MAX_DEPTH = 12
_KEYS = {
    "schema_version", "authority", "source_origin", "document_utf8_b64",
    "source_sha256", "reviewed_text", "reviewed_sha256", "review_revision",
}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_SESSION = re.compile(r"[A-Za-z0-9._:-]{1,80}\Z", re.ASCII)


def _invalid() -> None:
    raise ValueError("transcript_handoff_invalid")


def _unique(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _shape(value: object, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        _invalid()
    if type(value) is dict:
        for key, child in value.items():
            _shape(key, depth + 1)
            _shape(child, depth + 1)
    elif type(value) is list:
        for child in value:
            _shape(child, depth + 1)
    elif type(value) is str:
        value.encode("utf-8", errors="strict")
    elif type(value) is float and not math.isfinite(value):
        _invalid()


def _json(raw: bytes) -> dict:
    if raw.startswith(b"\xef\xbb\xbf"):
        _invalid()
    value = json.loads(
        raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique,
        parse_constant=lambda _: _invalid(),
    )
    if type(value) is not dict:
        _invalid()
    _shape(value)
    return value


def _read_envelope() -> dict:
    # EOF is mandatory: a bounded pipe is not a deadline for an arbitrary producer.
    if sys.stdin.isatty():
        _invalid()
    binary = getattr(sys.stdin, "buffer", None)
    if binary is not None:
        raw = binary.read(MAX_ENVELOPE_BYTES + 1)
    else:
        source = sys.stdin.read(MAX_ENVELOPE_BYTES + 1)
        if type(source) is not str:
            _invalid()
        raw = source.encode("utf-8", errors="strict")
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_ENVELOPE_BYTES:
        _invalid()
    return _json(raw)


def _validate(envelope: dict) -> tuple[dict, str, str, int]:
    if (set(envelope) != _KEYS
            or envelope["schema_version"] != "jarvis-transcript-handoff-v1"
            or envelope["authority"] != "none"
            or envelope["source_origin"] != "unverified"
            or type(envelope["document_utf8_b64"]) is not str
            or type(envelope["review_revision"]) is not int
            or not 1 <= envelope["review_revision"] <= 2**31 - 1):
        _invalid()
    for key in ("source_sha256", "reviewed_sha256"):
        if type(envelope[key]) is not str or _HASH.fullmatch(envelope[key]) is None:
            _invalid()
    encoded = envelope["document_utf8_b64"]
    if not 1 <= len(encoded) <= 4 * ((MAX_DOCUMENT_BYTES + 2) // 3):
        _invalid()
    raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    if (not 1 <= len(raw) <= MAX_DOCUMENT_BYTES
            or base64.b64encode(raw).decode("ascii") != encoded
            or hashlib.sha256(raw).hexdigest() != envelope["source_sha256"]):
        _invalid()
    document = _json(raw)
    # Existing local review contracts are the single source of ASR/text semantics.
    # These imports are deliberately after opt-in, argv checks and byte/hash checks.
    from apps.jarvis_voice.transcript_review import _document, _text

    _document(document)
    text = _text(envelope["reviewed_text"])
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != envelope["reviewed_sha256"]:
        _invalid()
    return document, text, envelope["source_sha256"], envelope["review_revision"]


def _tts_location(result) -> dict[str, str] | None:
    """Portable lab locator only; never weaken the console's private-path redaction."""
    if result.output_path is None or result.status != "completed":
        return None
    path = Path(result.output_path)
    base = Path(tempfile.gettempdir()).absolute()
    if (not path.is_absolute() or path.name != "sample.wav" or path.parent.parent != base
            or re.fullmatch(r"jarvis-voice-lab-[0-9a-f]{32}-[A-Za-z0-9_-]{1,64}",
                            path.parent.name) is None):
        return None
    return {"base": "system_temporary_directory",
            "relative_path": f"{path.parent.name}/sample.wav"}


def run_transcript_review(args, core_factory, *, lab_runner=None) -> CommandExecutionResult:
    """One new authorized local turn; never retry or downgrade a Core failure."""
    if getattr(args, "authorized", None) is not True:
        raise ConsoleCommandError(
            "Transcript handoff requires explicit --authorized local consent.",
            error_code="transcript_handoff_not_authorized",
            exit_code=ConsoleExitCode.USAGE_ERROR,
        )
    try:
        if (type(args.include_content) is not bool or type(args.session_id) is not str
                or _SESSION.fullmatch(args.session_id) is None or not callable(core_factory)):
            _invalid()
        from apps.jarvis_console.transcript_tts_options import transcript_tts_config

        tts_config = transcript_tts_config(args)
        document, text, source_hash, declaration = _validate(_read_envelope())
        if tts_config is not None:
            from apps.jarvis_console.persistent_tts import preflight_local_tts_config

            preflight_local_tts_config(tts_config)

        from apps.jarvis_console.voice_pilot import ReviewedVoiceCorePort
        from apps.jarvis_voice.transcript_review import LocalTranscriptReview
        from shared.contracts import SurfaceIdentityContract

        identity = SurfaceIdentityContract(
            surface_id="surface://local-transcript-review", surface_kind="voice",
            surface_session_id=args.session_id, surface_capability_scope=[],
            operator_identity_ref="operator://local_console",
            canonical_user_ref="user://local_operator",
        )
        review = LocalTranscriptReview(identity=identity)
        review.consent(identity, granted=True)
        ticket = review.propose(document, identity=identity, source_sha256=source_hash,
                                deadline_seconds=120)
        view = review.review(ticket, identity=identity)
        if view is None:
            _invalid()
        if view.text != text:
            view = review.edit(ticket, text, identity=identity)
        if view is None:
            _invalid()
        request = review.confirm(ticket, identity=identity, candidate_hash=view.candidate_hash,
                                 revision=view.revision)
        if request is None:
            _invalid()
        # Only this point may bootstrap a persistent runtime. A downloaded revision
        # never substitutes for the fresh Python ticket/confirmation above.
        port = ReviewedVoiceCorePort(core_factory(), identity, transcript_review=review)
        final = port.interact(request)
        response = port.response
        payload = {
            "mode": "local_transcript_handoff", "state": review.snapshot()["state"],
            "authority": "none", "source_origin": "unverified",
            "declared_review_revision": declaration,
            "local_review_revision": view.revision, "core_evidence_mode": "core_local",
            "operator_authenticated": False, "speaker_identification": False,
            "hardware_audio": False, "runtime_capability_promoted": False,
            "operation_dispatched": response.operation_dispatch is not None,
            "canonical_turn_recorded": bool(response.memory_record.memory_record_id),
            "governance_decision": response.governance_decision.decision.value,
            "core_event_count": len(response.events), "review_event_count": len(review.events()),
            "content_included": False, "content_withheld": False,
        }
        redactor = ConsoleRuntime(
            output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
        )
        if tts_config is not None:
            from apps.jarvis_console.persistent_tts import speak_persisted_final

            # Audio failure is not Core failure: a canonical turn has already
            # committed. Never retry Core or suppress its textual final here.
            try:
                speech = speak_persisted_final(
                    config=tts_config, port=port, request=request, final=final,
                    lab_runner=lab_runner,
                )
                payload["tts"] = speech.metadata()
                if getattr(args, "tts_show_output_path", None) is True:
                    location = _tts_location(speech)
                    if _requires_redaction(location, redactor):
                        location = None
                    payload["tts"]["output_location"] = location
                    payload["tts"]["output_location_available"] = location is not None
            except Exception:
                payload["tts"] = {
                    "status": "failed", "reason": "local_tts_unavailable",
                    "engine": tts_config.engine, "audio_evidence_mode": "not_run",
                    "artifact_available": False, "final_character_count": len(final.text),
                    "text_fallback_available": True, "audit_event_recorded": False,
                }
        if args.include_content:
            content = {"reviewed_text": text, "final_text": final.text}
            if _requires_redaction(content, redactor):
                payload["content_withheld"] = True
                payload["content_withheld_reason"] = "sensitive_display_content"
            else:
                payload.update(content)
                payload["content_included"] = True
        _shape(payload)
        encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True)
        if len(encoded.encode("ascii")) > 262_144 or redactor.redact(encoded)[1]:
            _invalid()
        return CommandExecutionResult(outputs=[encoded])
    except Exception:
        raise ConsoleCommandError(
            "Transcript handoff refused; check consent, bounded stdin review and local Core.",
            error_code="transcript_handoff_refused", exit_code=ConsoleExitCode.USAGE_ERROR,
        ) from None
