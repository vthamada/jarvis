"""Bounded, offline lexical review of caller-supplied, untrusted evidence.

This module neither fetches sources nor answers a question. Quotes are review
candidates, not validated facts or the Core's final synthesis.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime

INPUT_SCHEMA = "jarvis-research-input-v1"
OUTPUT_SCHEMA = "jarvis-research-dossier-v1"
MAX_DOCUMENT_BYTES = 64 * 1024
MAX_SOURCES = 16
MAX_QUERY_CHARACTERS = 2048
MAX_SOURCE_BYTES = 16 * 1024
MAX_CITATIONS = 8
MAX_QUOTE_CHARACTERS = 512
MAX_TOTAL_QUOTE_CHARACTERS = 4096
_SOURCE_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z",
    re.ASCII,
)
_TOKENS = re.compile(r"[^\W_]+", re.UNICODE)
_SENTENCES = re.compile(r"[^.!?。\n]+[.!?。]?", re.UNICODE)
_BIDI_CONTROLS = {0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F), *range(0x2066, 0x206A)}


def _fail(code: str) -> None:
    raise ValueError(code)


def _utf8(value: str) -> bytes:
    try:
        return value.encode("utf-8")
    except UnicodeError:
        _fail("research_invalid_unicode")
    raise AssertionError("unreachable")


def _digest(value: str) -> str:
    return hashlib.sha256(_utf8(value)).hexdigest()


def _check_text_controls(value: str) -> None:
    if any(
        (ord(char) < 32 and char not in "\t\r\n")
        or 0x7F <= ord(char) <= 0x9F
        or ord(char) in _BIDI_CONTROLS
        for char in value
    ):
        _fail("research_unsafe_text_controls")


def _timestamp(value: object) -> datetime:
    if type(value) is not str or len(value) > 64 or not _TIMESTAMP.fullmatch(value):
        _fail("research_invalid_timestamp")
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            _fail("research_invalid_timestamp")
        return parsed.astimezone(UTC)
    except (ValueError, OverflowError):
        _fail("research_invalid_timestamp")
    raise AssertionError("unreachable")


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKENS.findall(unicodedata.normalize("NFC", text))]


def _canonical_digest(value: object) -> str:
    return _digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _validated(document: object) -> tuple[str, datetime, list[dict]]:
    if type(document) is not dict or set(document) != {
        "schema_version",
        "query",
        "as_of",
        "sources",
    }:
        _fail("research_invalid_envelope")
    if type(document["schema_version"]) is not str or document["schema_version"] != INPUT_SCHEMA:
        _fail("research_invalid_schema_version")
    query = document["query"]
    if type(query) is not str or not 1 <= len(query) <= MAX_QUERY_CHARACTERS:
        _fail("research_invalid_query")
    _check_text_controls(query)
    if not _tokens(query):
        _fail("research_invalid_query")
    as_of = _timestamp(document["as_of"])
    sources = document["sources"]
    if type(sources) is not list or len(sources) > MAX_SOURCES:
        _fail("research_invalid_sources")
    seen = set()
    validated = []
    for source in sources:
        if type(source) is not dict or set(source) != {
            "source_ref",
            "text",
            "observed_at",
            "expires_at",
        }:
            _fail("research_invalid_source")
        source_ref = source["source_ref"]
        if type(source_ref) is not str or not _SOURCE_REF.fullmatch(source_ref):
            _fail("research_invalid_source_ref")
        if source_ref in seen:
            _fail("research_duplicate_source_ref")
        seen.add(source_ref)
        text = source["text"]
        if (
            type(text) is not str
            or len(text) > MAX_SOURCE_BYTES
            or len(_utf8(text)) > MAX_SOURCE_BYTES
        ):
            _fail("research_invalid_source_text")
        _check_text_controls(text)
        observed_at = _timestamp(source["observed_at"])
        expires_at = None if source["expires_at"] is None else _timestamp(source["expires_at"])
        if expires_at is not None and expires_at < observed_at:
            _fail("research_invalid_validity_interval")
        if observed_at > as_of:
            currentness = "future"
        elif expires_at is not None and expires_at <= as_of:
            currentness = "stale"
        elif expires_at is None:
            currentness = "unknown"
        else:
            currentness = "current"
        validated.append(
            {
                "source_ref": source_ref,
                "text": text,
                "text_sha256": _digest(text),
                "observed_at": observed_at.isoformat(),
                "expires_at": None if expires_at is None else expires_at.isoformat(),
                "currentness": currentness,
            }
        )
    # Bounds also apply to callers that bypass the console's bounded JSON reader.
    encoded = _utf8(json.dumps(document, ensure_ascii=False, separators=(",", ":")))
    if len(encoded) > MAX_DOCUMENT_BYTES:
        _fail("research_document_too_large")
    return query, as_of, sorted(validated, key=lambda source: source["source_ref"])


def _spans(text: str):
    """Yield exact original offsets, with a documented fixed window limit."""
    for sentence in _SENTENCES.finditer(text):
        start, end = sentence.span()
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        for offset in range(start, end, MAX_QUOTE_CHARACTERS):
            yield offset, min(offset + MAX_QUOTE_CHARACTERS, end)


def build_offline_research_dossier(document: dict, *, include_content: bool = False) -> dict:
    """Return deterministic metadata or opt-in untrusted quote candidates.

    Unknown expiry is reviewable but never described as current. Future and
    expired evidence is withheld. All times are declarations, not clock proofs.
    """
    if type(include_content) is not bool:
        _fail("research_invalid_content_option")
    query, as_of, sources = _validated(document)
    query_tokens = set(_tokens(query))
    counts = {code: 0 for code in ("current", "stale", "future", "unknown")}
    ranked = []
    for source in sources:
        counts[source["currentness"]] += 1
        if source["currentness"] not in {"current", "unknown"}:
            continue
        best = None
        for start, end in _spans(source["text"]):
            quote = source["text"][start:end]
            tokens = _tokens(quote)
            matches = query_tokens.intersection(tokens)
            if not matches:
                continue
            occurrence_count = sum(token in query_tokens for token in tokens)
            key = (-len(matches), -occurrence_count, source["source_ref"], start, end)
            candidate = {
                "source_ref": source["source_ref"],
                "text_sha256": source["text_sha256"],
                "quote": quote,
                "span": {
                    "start": start,
                    "end": end,
                    "unit": "unicode_code_points",
                    "end_exclusive": True,
                },
                "matched_query_token_count": len(matches),
                "currentness": source["currentness"],
                "observed_at": source["observed_at"],
                "expires_at": source["expires_at"],
                "untrusted_evidence": True,
                "authority": "none",
            }
            if best is None or key < best[0]:
                best = (key, candidate, matches)
        if best is not None:
            ranked.append(best)
    ranked.sort(key=lambda item: item[0])
    selected = ranked[:MAX_CITATIONS]
    candidates = [item[1] for item in selected]
    matched_tokens = set().union(*(item[2] for item in selected))
    eligible_count = counts["current"] + counts["unknown"]
    status = (
        "review_candidates_available"
        if candidates
        else ("no_eligible_evidence" if not eligible_count else "no_lexical_match")
    )
    manifest = [
        {key: value for key, value in source.items() if key != "text"} for source in sources
    ]
    result = {
        "schema_version": OUTPUT_SCHEMA,
        "status": status,
        "draft": True,
        "requires_human_review": True,
        "read_only": True,
        "authority": "none",
        "evidence_mode": "supplied_text_lexical",
        "truth_assessment": "not_assessed",
        "conflict_assessment": "not_assessed",
        "timestamps": "caller_declared_not_verified",
        "as_of": as_of.isoformat(),
        "currentness": "current"
        if candidates and all(candidate["currentness"] == "current" for candidate in candidates)
        else "unknown",
        "method": {
            "tokenization": "unicode_words_nfc_casefold_exact_overlap",
            "ranking": "distinct_query_tokens_then_occurrences_then_source_ref_then_offset",
            "selection": "one_best_span_per_source",
            "quote_window_characters": MAX_QUOTE_CHARACTERS,
            "semantic_relevance": "not_assessed",
            "source_instructions": "untrusted_data_without_authority",
        },
        "counts": {
            "sources": len(sources),
            "source_currentness": counts,
            "eligible_sources": eligible_count,
            "withheld_sources": counts["stale"] + counts["future"],
            "matching_sources": len(ranked),
            "selected_citations": len(candidates),
            "query_tokens": len(query_tokens),
            "matched_query_tokens": len(matched_tokens),
            "quote_characters": sum(len(candidate["quote"]) for candidate in candidates),
        },
        "fingerprints": {
            "query_sha256": _digest(query),
            "source_manifest_sha256": _canonical_digest(manifest),
            "source_text_sha256": sorted(source["text_sha256"] for source in sources),
        },
        "content_included": include_content,
    }
    if include_content:
        result["query"] = query
        result["review_candidates"] = candidates
    return result
