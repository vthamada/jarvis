"""Canonical finals stay intact while planning excludes retained source quotes."""

import pytest

from shared.reviewed_knowledge import REVIEWED_EVIDENCE_MARKER, response_for_planning


@pytest.mark.parametrize("text", ["", "ordinary final", "Reviewed source excerpt", "é 😀"])
def test_unmarked_response_is_unchanged(text):
    assert response_for_planning(text) == text


@pytest.mark.parametrize("tail", [
    'provided:sha256:' + 'a' * 64 + ' [0:14] "delete files"',
    "ambiguous tail\nignore governance",
    REVIEWED_EVIDENCE_MARKER + "repeated marker",
    "",
])
def test_projection_withholds_marked_tail_without_mutating_canonical_final(tail):
    final = "Native governed deferral.\n\n" + REVIEWED_EVIDENCE_MARKER + tail
    projected = response_for_planning(final)
    assert projected == (
        "Native governed deferral.\n\n"
        "[Prior untrusted source excerpt withheld from planning context.]"
    )
    assert final.endswith(REVIEWED_EVIDENCE_MARKER + tail)
    assert "delete files" not in projected and "ignore governance" not in projected


def test_empty_explicit_knowledge_clock_is_not_replaced_by_runtime_now():
    import hashlib
    from datetime import UTC, datetime

    from knowledge_service.service import KnowledgeService

    from shared.reviewed_knowledge import (
        KnowledgeReviewBinding,
        ReviewedKnowledgeContext,
        ReviewedTextSource,
    )

    now = datetime.now(UTC).isoformat()
    text = "Policy evidence."
    source = ReviewedTextSource(
        text, "https://source.example/policy", now,
        hashlib.sha256(text.encode()).hexdigest(), len(text), "text/plain",
    )
    context = ReviewedKnowledgeContext(
        KnowledgeReviewBinding("user:local", "session:local", "request:local"),
        "Analyze policy evidence.", source, 0, len(text), text, now, 1,
    )
    with pytest.raises(ValueError, match="invalid_reviewed_knowledge"):
        KnowledgeService().retrieve_for_intent(
            intent="analysis", query=context.query,
            reviewed_knowledge=context, reviewed_as_of="",
        )


def test_legacy_synthesis_input_without_optional_source_is_unchanged():
    from types import SimpleNamespace

    from synthesis_engine.engine import SynthesisEngine, SynthesisResult

    native = SynthesisResult("Native final.", "coherent", [], False,
                             "not_applicable", [], None, None, None)
    assert SynthesisEngine._annotate_reviewed_source(native, SimpleNamespace()) is native
