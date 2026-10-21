"""Import a bounded static REA projection through the sovereign reviewed-source Core.

This bridge does not execute REA, authenticate a producer or verify its semantic
digests. Consent flags declare a local selection, not a runtime execution grant.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from apps.jarvis_console import source_review_cli
from apps.jarvis_rea.evidence import project_evidence

QUERY = "Analyze JavaScript static analysis evidence in read-only mode."
SOURCE_URL = "https://github.com/vthamada/rea/tree/00a055be0fad728e1ba183c8de968d5538ba11ef"
_SESSION = re.compile(r"[A-Za-z0-9._:-]{1,80}\Z", re.ASCII)


def _invalid():
    raise ValueError("invalid_rea_evidence_input")


def _validate_options(authorized, confirmed, session_id, include_content, core_factory):
    if (
        authorized is not True
        or confirmed is not True
        or type(session_id) is not str
        or not _SESSION.fullmatch(session_id)
        or type(include_content) is not bool
        or (core_factory is not None and not callable(core_factory))
    ):
        _invalid()


def review_evidence(
    document,
    *,
    authorized,
    confirmed,
    session_id,
    include_content=False,
    core_factory=None,
):
    """Review one projected static import, preserving the exact canonical final.

    Only locally constructed labels, bounded counts and coverage values cross the
    evidence boundary. Raw graphs, paths and producer instructions never enter the
    Core query or its reviewed quote. The fixed URL identifies the adapter's
    reference revision; it is not proof of the supplied document's origin.
    """
    try:
        _validate_options(authorized, confirmed, session_id, include_content, core_factory)
        projection = project_evidence(document)
        text = projection.summary
        raw = text.encode("utf-8", errors="strict")
        digest = hashlib.sha256(raw).hexdigest()
        # The timestamp marks this local import, not an authenticated REA run.
        source = {
            "text": text,
            "source_url": SOURCE_URL,
            "observed_at": datetime.now(UTC).isoformat(),
            "content_sha256": digest,
            "byte_count": len(raw),
            "media_type": "text/plain",
            "expires_at": None,
        }
        selected = {
            "schema_version": source_review_cli.INPUT_SCHEMA,
            "authority": "none",
            "origin_status": "declared_unverified",
            "query": QUERY,
            "source": source,
            "selection": {
                "start": 0, "end": len(text), "quote": text, "content_sha256": digest,
            },
        }
        result = source_review_cli.observe_document(
            selected,
            authorized=authorized,
            confirmed=confirmed,
            session_id=session_id,
            include_content=include_content,
            core_factory=core_factory,
        )
        return {
            **result,
            "rea_provider_id": projection.provider_id,
            "rea_root_sha256": projection.root_sha256,
            "rea_counts": dict(projection.counts),
            "rea_call_governed_by_core": False,
            "rea_semantic_digest_verified": False,
        }
    except Exception:
        raise ValueError("invalid_rea_evidence_input") from None
