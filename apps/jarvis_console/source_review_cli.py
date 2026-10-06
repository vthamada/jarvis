"""Explicit stdin-only source review dispatched through the sovereign local Core.

Consent flags are local declarations, not authenticated identity or an execution
grant. Supplied source instructions remain isolated evidence. The normal Core
memory policy persists its canonical final response, including selected quotes.
This command never fetches a URL or ingests a source into the curated corpus.
All seven source fields are mandatory, including expires_at (null if unknown).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.review_input import (
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    _requires_redaction,
    read_review_input,
)
from apps.jarvis_console.runtime import ConsoleRuntime

INPUT_SCHEMA = "jarvis-source-review-v1"
OUTPUT_SCHEMA = "jarvis-source-review-result-v1"
_SESSION = re.compile(r"[A-Za-z0-9._:-]{1,80}\Z", re.ASCII)
_ENVELOPE_KEYS = {"schema_version", "authority", "origin_status", "query", "source", "selection"}
_SOURCE_KEYS = {
    "text",
    "source_url",
    "observed_at",
    "content_sha256",
    "byte_count",
    "media_type",
    "expires_at",
}
_SELECTION_KEYS = {"start", "end", "quote", "content_sha256"}


def _invalid():
    raise ValueError("invalid_source_review_input")


def _utc_now():
    return datetime.now(UTC).isoformat()


def _options(authorized, confirmed, session_id, include_content, core_factory):
    if authorized is not True or confirmed is not True:
        _invalid()
    if (
        type(session_id) is not str
        or not _SESSION.fullmatch(session_id)
        or type(include_content) is not bool
        or (core_factory is not None and not callable(core_factory))
    ):
        _invalid()


def _validate(document, binding, stamp):
    from shared.reviewed_knowledge import (
        ReviewedKnowledgeContext,
        ReviewedTextSource,
        validate_context,
    )

    if (
        type(document) is not dict
        or set(document) != _ENVELOPE_KEYS
        or type(document["schema_version"]) is not str
        or document["schema_version"] != INPUT_SCHEMA
        or type(document["authority"]) is not str
        or document["authority"] != "none"
        or type(document["origin_status"]) is not str
        or document["origin_status"] != "declared_unverified"
        or type(document["source"]) is not dict
        or set(document["source"]) != _SOURCE_KEYS
        or type(document["selection"]) is not dict
        or set(document["selection"]) != _SELECTION_KEYS
    ):
        _invalid()
    # No source dictionary is retained: shared validation copies all fields and
    # checks bounded UTF-8 bytes, controls, exact hashes, URL and UTC timestamps.
    source = ReviewedTextSource(**document["source"])
    selection = document["selection"]
    if (
        type(selection["content_sha256"]) is not str
        or selection["content_sha256"] != source.content_sha256
    ):
        _invalid()
    context = validate_context(
        ReviewedKnowledgeContext(
            binding=binding,
            query=document["query"],
            source=source,
            start=selection["start"],
            end=selection["end"],
            quote=selection["quote"],
            reviewed_at=stamp,
            revision=1,
        ),
        binding=binding,
        as_of=stamp,
    )
    # The public Python entry point has the same total-document budget as stdin.
    encoded = json.dumps(document, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_INPUT_BYTES:
        _invalid()
    return context


def _default_core_factory():
    from apps.jarvis_console.cli import JarvisConsole

    return JarvisConsole.build(
        runtime_dir=ROOT / ".jarvis_runtime" / "console",
        local_observability_only=True,
    ).orchestrator


def _encoded(payload):
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True)
    if len(encoded.encode("ascii")) > MAX_OUTPUT_BYTES:
        _invalid()
    return encoded


def _readback(core, contract, response, expected_quote, expected_rendering, review):
    from memory_service.repository import StoredTurn

    from shared.contracts import MemoryRecordContract
    from shared.events import InternalEventEnvelope
    from shared.types import PermissionDecision

    final = response.response_text
    record = response.memory_record
    decision = response.governance_decision.decision
    if (
        type(final) is not str
        or not final
        or type(record) is not MemoryRecordContract
        or type(record.memory_record_id) is not str
        or not record.memory_record_id.strip()
        or record.record_type != "interaction_turn"
        or record.source_service != "memory-service"
        or record.session_id != contract.session_id
        or record.user_id != contract.user_id
        or record.mission_id != contract.mission_id
        or type(record.timestamp) is not str
        or type(record.payload) is not dict
        or type(decision) is not PermissionDecision
        or response.request_id != contract.request_id
        or response.session_id != contract.session_id
        or response.intent != "analysis"
        or review.snapshot()["state"] != "handed_off"
        or any(
            getattr(response, name, False) is not None
            for name in (
                "operation_dispatch",
                "operation_result",
                "adapter_grant",
                "adapter_grant_claim",
                "action_confirmation_claim",
                "action_confirmation_challenge",
                "adapter_action_intent",
            )
        )
    ):
        _invalid()
    final.encode("utf-8", errors="strict")
    if any(
        record.payload.get(key) != value
        for key, value in {
            "request_content": contract.content,
            "response_text": final,
            "intent": "analysis",
            "governance_decision": decision.value,
        }.items()
    ):
        _invalid()
    stamp, record_id = record.timestamp, record.memory_record_id
    # This is a persisted-turn check, not a claim that review verified a source.
    # StoredTurn has no request ID; the persisted memory event supplies that link.
    turns = core.memory_service.repository.fetch_recent_turns(str(contract.session_id), 5)
    if (
        type(turns) is not list
        or len(turns) > 5
        or any(type(turn) is not StoredTurn for turn in turns)
        or not any(
            turn.session_id == contract.session_id
            and turn.mission_id == contract.mission_id
            and turn.user_id == contract.user_id
            and turn.request_content == contract.content
            and turn.response_text == final
            and turn.intent == "analysis"
            and turn.timestamp == stamp
            for turn in turns
        )
    ):
        _invalid()
    names = ("governance_checked", "response_synthesized", "memory_recorded")
    events = core.observability_service.repository.list_events(
        limit=10,
        event_names=names,
        request_id=str(contract.request_id),
        session_id=str(contract.session_id),
    )
    if (
        type(events) is not list
        or len(events) != 3
        or any(
            type(event) is not InternalEventEnvelope
            or type(event.payload) is not dict
            or event.request_id != contract.request_id
            or event.session_id != contract.session_id
            for event in events
        )
        or {event.event_name for event in events} != set(names)
    ):
        _invalid()
    by_name = {event.event_name: event.payload for event in events}
    memory = by_name["memory_recorded"]
    synthesis = by_name["response_synthesized"]
    if (
        memory.get("memory_record_id") != record_id
        or memory.get("record_type") != "interaction_turn"
        or by_name["governance_checked"].get("decision") != decision.value
        or synthesis.get("intent") != "analysis"
    ):
        _invalid()
    status = synthesis.get("reviewed_source_status")
    count = synthesis.get("reviewed_source_quote_characters")
    if (
        type(status) is not str
        or status not in {"quoted_for_review", "withheld", "refused"}
        or type(count) is not int
        or not 0 <= count <= 512
        or (status == "quoted_for_review" and count != len(expected_quote))
        or (status == "quoted_for_review" and expected_rendering not in final)
        or (status != "quoted_for_review" and count != 0)
    ):
        _invalid()
    return final, decision.value, status, count


def observe_document(
    document,
    *,
    authorized=False,
    confirmed=False,
    session_id=None,
    include_content=False,
    core_factory=None,
):
    """Confirm one exact local selection before constructing or calling Core.

    Default output is content-free status/counts. Explicit content consists only
    of the canonical Core response; sensitive content is withheld as a whole.
    This Python entry point, like stdin, fails with a fixed non-disclosing error.
    """
    try:
        _options(authorized, confirmed, session_id, include_content, core_factory)
        ensure_src_paths()
        from executive_engine.engine import ExecutiveEngine
        from knowledge_service.source_review import LocalKnowledgeReview

        from shared.contracts import InputContract
        from shared.reviewed_knowledge import (
            KnowledgeReviewBinding,
            render_reviewed_evidence,
            validate_context,
        )
        from shared.types import ChannelType, InputType, RequestId, SessionId

        stamp = _utc_now()
        request_id = "req-source-review-" + uuid4().hex
        principal = "user://local_operator"
        binding = KnowledgeReviewBinding(principal, session_id, request_id)
        selected = _validate(document, binding, stamp)
        contract = InputContract(
            request_id=RequestId(request_id),
            session_id=SessionId(session_id),
            channel=ChannelType.CONSOLE,
            input_type=InputType.TEXT,
            content=selected.query,
            timestamp=stamp,
            user_id=principal,
            metadata={},
            attachments=[],
            surface_id="surface://local-source-review",
            surface_kind="console",
            surface_session_id=session_id,
            surface_capability_scope=[],
            operator_identity_ref="operator://local_console",
            canonical_user_ref=principal,
            requested_autonomy_level="assist_only",
            max_autonomy_level="assist_only",
        )
        directive = ExecutiveEngine().direct(contract)
        if (
            directive.intent != "analysis"
            or directive.requires_clarification
            or not directive.should_query_knowledge
            or directive.should_execute_operation
        ):
            _invalid()
        review = LocalKnowledgeReview(binding, wall_clock=_utc_now)
        review.consent(binding, granted=True)
        ticket = review.propose(selected.source, selected.query, binding=binding)
        view = review.review(ticket, binding=binding)
        if view is None:
            _invalid()
        view = review.select(ticket, binding=binding, start=selected.start, end=selected.end)
        if view is None or view.quote != selected.quote:
            _invalid()
        context = review.confirm(
            ticket, binding=binding, fingerprint=view.fingerprint, revision=view.revision
        )
        if (
            context is None
            or context.start != selected.start
            or context.end != selected.end
            or context.quote != selected.quote
            or context.source.content_sha256 != selected.source.content_sha256
        ):
            _invalid()
        # Snapshot the fresh confirmed context before Core callbacks. Rendering
        # is compared with its persisted final, not revalidated against a later
        # clock: a historically recorded quotation cannot become unrecorded by
        # expiry after dispatch.
        confirmed_context = validate_context(
            context,
            binding=binding,
            query=selected.query,
            as_of=_utc_now(),
        )
        expected_rendering = render_reviewed_evidence(confirmed_context)
        # Validation, fresh local review and exact confirmation precede any store
        # construction. No retry after Core receives the one-shot reviewed ticket.
        factory = _default_core_factory if core_factory is None else core_factory
        core = factory()
        expected = replace(contract, metadata={}, attachments=[], surface_capability_scope=[])
        response = core.handle_input(contract, reviewed_knowledge=context, knowledge_review=review)
        final, decision, source_status, quote_count = _readback(
            core, expected, response, confirmed_context.quote, expected_rendering, review
        )
        payload = {
            "schema_version": OUTPUT_SCHEMA,
            "status": "recorded",
            "mode": "local_source_review",
            "authority": "none",
            "origin_status": "declared_unverified",
            "operator_authenticated": False,
            "runtime_capability_promoted": False,
            "network_io": False,
            "content_included": False,
            "content_withheld": False,
            "content_withheld_reason": None,
            "review_state": review.snapshot()["state"],
            "review_event_count": len(review.events()),
            "core_event_count": len(response.events),
            "canonical_turn_recorded": True,
            "operation_dispatched": False,
            "governance_decision": decision,
            "reviewed_source_status": source_status,
            "reviewed_source_quote_characters": quote_count,
            "response_character_count": len(final),
        }
        redactor = ConsoleRuntime(
            output_format="json", sensitive_paths=(str(ROOT), str(Path.home()))
        )
        if include_content:
            content = {"response_text": final}
            # Canonical evidence rendering escapes Markdown metacharacters; that
            # can hide credential/path patterns from the display heuristic. Check
            # the exact, validated raw selection as well, without exposing it or
            # altering the already persisted canonical response. This is pattern
            # based display protection, not a general secret-detection guarantee.
            display_review = {"response_text": final, "selected_quote": selected.quote}
            if _requires_redaction(display_review, redactor):
                payload["content_withheld"] = True
                payload["content_withheld_reason"] = "sensitive_display_content"
            else:
                payload.update(content)
                payload["content_included"] = True
        if redactor.redact(_encoded(payload))[1]:
            _invalid()
        return payload
    except Exception:
        raise ValueError("invalid_source_review_input") from None


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        _invalid()


def main(argv=None):
    parser = _SafeParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--confirm-reviewed-selection", action="store_true", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--include-content", action="store_true")
    try:
        args = parser.parse_args(argv)
        _options(
            args.authorized,
            args.confirm_reviewed_selection,
            args.session_id,
            args.include_content,
            None,
        )
        document = read_review_input()
        payload = observe_document(
            document,
            authorized=args.authorized,
            confirmed=args.confirm_reviewed_selection,
            session_id=args.session_id,
            include_content=args.include_content,
        )
        print(_encoded(payload))
        return 0
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"cancelled","authority":"none"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"invalid_source_review_input","authority":"none"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
