"""Strict, bounded input projection onto the existing in-memory patch reviewer.

The caller supplies every source explicitly. No paths are opened, no code runs,
and a successful review is neither permission nor evidence of executed tests.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict

from operational_service.adapters.code_sandbox.patch_review import (
    FileEdits,
    PatchProposal,
    PatchReviewer,
    ReviewLimits,
    TextEdit,
)

INPUT_SCHEMA = "jarvis-code-review-input-v1"
OUTPUT_SCHEMA = "jarvis-code-review-output-v1"
MAX_INPUT_BYTES = 65536
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_INPUT_ERROR = "code_review_input_invalid"
_REVIEW_ERROR = "code_review_rejected"


def _keys(value: object, expected: set[str]) -> dict:
    if (
        type(value) is not dict
        or len(value) != len(expected)
        or any(type(key) is not str for key in value)
        or set(value) != expected
    ):
        raise ValueError(_INPUT_ERROR)
    return value


def _text(value: object, maximum: int, *, empty: bool = False) -> str:
    if type(value) is not str or not (0 if empty else 1) <= len(value) <= maximum:
        raise ValueError(_INPUT_ERROR)
    try:
        if len(value.encode("utf-8")) > maximum:
            raise ValueError(_INPUT_ERROR)
    except UnicodeError:
        raise ValueError(_INPUT_ERROR) from None
    return value


def _hash(value: object) -> str:
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ValueError(_INPUT_ERROR)
    return value


def _validate(document: object, limits: ReviewLimits) -> None:
    """Validate all structural types and collection bounds before dataclasses."""
    envelope = _keys(document, {"schema_version", "files", "proposal"})
    if type(envelope["schema_version"]) is not str or envelope["schema_version"] != INPUT_SCHEMA:
        raise ValueError(_INPUT_ERROR)
    sources = envelope["files"]
    if type(sources) is not dict or not 1 <= len(sources) <= limits.max_files:
        raise ValueError(_INPUT_ERROR)
    total_bytes = 0
    for path, source in sources.items():
        _text(path, 180)
        _text(source, limits.max_file_bytes)
        total_bytes += len(source.encode("utf-8"))
        if total_bytes > limits.max_total_bytes:
            raise ValueError(_INPUT_ERROR)
    proposal = _keys(envelope["proposal"], {"expected_snapshot_sha256", "files"})
    _hash(proposal["expected_snapshot_sha256"])
    changes = proposal["files"]
    if type(changes) is not list or not 1 <= len(changes) <= limits.max_changed_files:
        raise ValueError(_INPUT_ERROR)
    total_edits = 0
    for change in changes:
        _keys(change, {"path", "expected_sha256", "edits"})
        _text(change["path"], 180)
        _hash(change["expected_sha256"])
        edits = change["edits"]
        if type(edits) is not list or not 1 <= len(edits) <= limits.max_edits:
            raise ValueError(_INPUT_ERROR)
        total_edits += len(edits)
        if total_edits > limits.max_edits:
            raise ValueError(_INPUT_ERROR)
        for edit in edits:
            _keys(edit, {"start", "end", "expected_text", "replacement"})
            if (
                type(edit["start"]) is not int
                or type(edit["end"]) is not int
                or not 0 <= edit["start"] < edit["end"] <= limits.max_file_bytes
            ):
                raise ValueError(_INPUT_ERROR)
            _text(edit["expected_text"], limits.max_file_bytes)
            _text(edit["replacement"], limits.max_file_bytes, empty=True)
    # Only validated JSON primitives remain; this bounds the standalone API as
    # well as the caller's bounded stdin. ASCII escaping is intentionally counted.
    if len(json.dumps(document, ensure_ascii=True).encode("ascii")) > MAX_INPUT_BYTES:
        raise ValueError(_INPUT_ERROR)


def build_code_review(document: dict, *, include_content: bool = False) -> dict:
    """Return a verified review draft, optionally disclosing source-bearing diff.

    The finite source dictionary defines the review allowlist, not effect scope
    or approval. Fingerprints establish consistency of the supplied bundle, not
    host freshness or trusted origin. Errors never expose partial content.
    """
    if type(include_content) is not bool:
        raise ValueError(_INPUT_ERROR)
    limits = ReviewLimits()
    _validate(document, limits)
    sources = dict(document["files"])
    try:
        reviewer = PatchReviewer(tuple(sources), limits)
        snapshot = reviewer.snapshot(sources)
    except ValueError:
        raise ValueError(_REVIEW_ERROR) from None
    proposal = PatchProposal(
        document["proposal"]["expected_snapshot_sha256"],
        tuple(
            FileEdits(
                change["path"],
                change["expected_sha256"],
                tuple(TextEdit(**edit) for edit in change["edits"]),
            )
            for change in document["proposal"]["files"]
        ),
    )
    # Capture the binding independently of the preview being verified, without
    # reproducing the reviewer's private fingerprint format in this interface.
    reference = reviewer.preview(snapshot, proposal)
    if reference.status != "reviewable" or reference.proposal_sha256 is None:
        raise ValueError(_REVIEW_ERROR)
    expected_proposal_sha256 = reference.proposal_sha256
    preview = reviewer.preview(snapshot, proposal)
    verified = reviewer.verify(preview, snapshot, expected_proposal_sha256=expected_proposal_sha256)
    if verified.status != "reviewable":
        raise ValueError(_REVIEW_ERROR)
    result = {
        "schema_version": OUTPUT_SCHEMA,
        "read_only": True,
        "draft": True,
        "requires_human_review": True,
        "telemetry": verified.telemetry(),
    }
    if include_content:
        result["content"] = {
            "diff": verified.diff,
            "files": [asdict(summary) for summary in verified.summaries],
        }
    return result
