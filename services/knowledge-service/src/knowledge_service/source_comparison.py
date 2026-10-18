"""Bounded exact comparison of supplied source spans, without semantic authority.

Dates and provenance are caller declarations. Matching strings do not prove
truth, disagreement is not semantic contradiction, and content fingerprints
are consistency checks rather than proof of independent origin.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime

from .research import (
    INPUT_SCHEMA as RESEARCH_INPUT_SCHEMA,
)
from .research import (
    MAX_DOCUMENT_BYTES,
    MAX_QUOTE_CHARACTERS,
    MAX_SOURCES,
    build_offline_research_dossier,
)

INPUT_SCHEMA = "jarvis-source-comparison-input-v1"
OUTPUT_SCHEMA = "jarvis-source-comparison-v1"
MAX_CLAIMS = 32
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z", re.ASCII)
_STATES = ("matching_text", "text_disagreement", "insufficient_evidence")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _utc(value: str) -> datetime:
    # The public research builder validates format and timezone before this call.
    return datetime.fromisoformat(value).astimezone(UTC)


def _validated(document: object) -> tuple[list[dict], list[dict], str]:
    if (type(document) is not dict or len(document) != 4
            or set(document) != {"schema_version", "as_of", "sources", "claims"}
            or type(document["schema_version"]) is not str
            or document["schema_version"] != INPUT_SCHEMA):
        raise ValueError()
    sources, claims = document["sources"], document["claims"]
    if (type(sources) is not list or not 1 <= len(sources) <= MAX_SOURCES
            or type(claims) is not list or not 1 <= len(claims) <= MAX_CLAIMS):
        raise ValueError()
    # Refuse large or nested source envelopes before delegating. Their scalar
    # fields and dates remain governed by the established research contract.
    for source in sources:
        if (type(source) is not dict or len(source) != 4
                or set(source) != {"source_ref", "text", "observed_at", "expires_at"}):
            raise ValueError()
    # Reuse the established source, control, Unicode, date and byte limits.
    # The fixed query has no bearing on which caller-bound spans are compared.
    build_offline_research_dossier({
        "schema_version": RESEARCH_INPUT_SCHEMA, "query": "source",
        "as_of": document["as_of"], "sources": sources,
    })
    as_of = _utc(document["as_of"])
    validated_sources = []
    by_ref = {}
    for source in sources:
        observed = _utc(source["observed_at"])
        expiry = None if source["expires_at"] is None else _utc(source["expires_at"])
        currentness = ("future" if observed > as_of else
                       "stale" if expiry is not None and expiry <= as_of else
                       "unknown" if expiry is None else "current")
        value = {
            "source_ref": source["source_ref"], "text": source["text"],
            "source_ref_sha256": _digest(source["source_ref"]),
            "text_sha256": _digest(source["text"]),
            "observed_at": observed.isoformat(),
            "expires_at": None if expiry is None else expiry.isoformat(),
            "currentness": currentness,
        }
        validated_sources.append(value)
        by_ref[value["source_ref"]] = value
    seen = set()
    validated_claims = []
    for claim in claims:
        if (type(claim) is not dict or len(claim) != 4
                or set(claim) != {"topic_ref", "source_ref", "start", "end"}
                or type(claim["topic_ref"]) is not str
                or not _REF.fullmatch(claim["topic_ref"])
                or type(claim["source_ref"]) is not str
                or not _REF.fullmatch(claim["source_ref"])
                or type(claim["start"]) is not int or type(claim["end"]) is not int):
            raise ValueError()
        source = by_ref.get(claim["source_ref"])
        start, end = claim["start"], claim["end"]
        if (source is None or not 0 <= start < end <= len(source["text"])
                or end - start > MAX_QUOTE_CHARACTERS):
            raise ValueError()
        identity = (claim["topic_ref"], claim["source_ref"], start, end)
        if identity in seen:
            raise ValueError()
        seen.add(identity)
        quote = source["text"][start:end]
        validated_claims.append({
            "topic_ref": claim["topic_ref"], "topic_ref_sha256": _digest(claim["topic_ref"]),
            "source_ref": claim["source_ref"],
            "source_ref_sha256": source["source_ref_sha256"],
            "text_sha256": source["text_sha256"], "quote_sha256": _digest(quote),
            "quote": quote, "start": start, "end": end,
            "currentness": source["currentness"],
        })
    # All fields are now shallow validated JSON primitives. Nested hostile
    # values are refused before serialization, not traversed recursively.
    if len(_canonical(document).encode("utf-8")) > MAX_DOCUMENT_BYTES:
        raise ValueError()
    validated_sources.sort(key=lambda source: source["source_ref_sha256"])
    validated_claims.sort(key=lambda claim: (
        claim["topic_ref_sha256"], claim["source_ref_sha256"], claim["start"], claim["end"],
    ))
    return validated_sources, validated_claims, as_of.isoformat()


def build_source_comparison(document: dict, *, include_content: bool = False) -> dict:
    """Return deterministic redacted metadata or explicitly opted-in review spans.

    Only declared current/unknown-expiry spans are eligible. Multiple copies of
    an identical whole source never suffice as separate comparison evidence.
    No network, persistence, model, review consent or Core dispatch is involved.
    """
    if type(include_content) is not bool:
        raise ValueError("source_comparison_invalid_content_option") from None
    try:
        sources, claims, as_of = _validated(document)
    except (ValueError, TypeError, KeyError, OverflowError, UnicodeError, RecursionError):
        raise ValueError("source_comparison_invalid_input") from None
    currentness = {state: 0 for state in ("current", "stale", "future", "unknown")}
    for source in sources:
        currentness[source["currentness"]] += 1
    groups = {}
    for claim in claims:
        groups.setdefault(claim["topic_ref_sha256"], []).append(claim)
    topics = []
    topic_states = dict.fromkeys(_STATES, 0)
    eligible_claims = []
    for topic_hash, group in sorted(groups.items()):
        eligible = [claim for claim in group if claim["currentness"] in {"current", "unknown"}]
        eligible_claims.extend(eligible)
        distinct_sources = {claim["text_sha256"] for claim in eligible}
        texts = {claim["quote"] for claim in eligible}
        state = ("insufficient_evidence" if len(distinct_sources) < 2 else
                 "matching_text" if len(texts) == 1 else "text_disagreement")
        topic_states[state] += 1
        topics.append({
            "topic_ref_sha256": topic_hash, "state": state,
            "counts": {"claims": len(group), "eligible_claims": len(eligible),
                       "withheld_claims": len(group) - len(eligible),
                       "distinct_eligible_source_texts": len(distinct_sources),
                       "distinct_eligible_span_texts": len(texts)},
            "authority": "none", "origin_status": "declared_unverified", "facts_verified": False,
        })
    manifest = [{key: value for key, value in source.items()
                 if key not in {"source_ref", "text"}} for source in sources]
    bindings = [{key: value for key, value in claim.items()
                 if key not in {"topic_ref", "source_ref", "quote"}} for claim in claims]
    result = {
        "schema_version": OUTPUT_SCHEMA,
        "read_only": True, "draft": True, "requires_human_review": True,
        "authority": "none", "origin_status": "declared_unverified", "facts_verified": False,
        "truth_assessment": "not_assessed", "semantic_conflict_assessment": "not_assessed",
        "timestamps": "caller_declared_not_verified",
        "currentness": "current" if eligible_claims and all(
            claim["currentness"] == "current" for claim in eligible_claims) else "unknown",
        "method": {
            "comparison": "exact_original_span_text",
            "independence": "distinct_source_content_not_verified_origin",
            "source_instructions": "untrusted_data_without_authority",
            "quote_window_characters": MAX_QUOTE_CHARACTERS,
        },
        "counts": {
            "sources": len(sources), "source_currentness": currentness,
            "claims": len(claims), "eligible_claims": len(eligible_claims),
            "withheld_claims": len(claims) - len(eligible_claims),
            "topics": len(topics), "topic_states": topic_states,
            "quote_characters": sum(claim["end"] - claim["start"] for claim in eligible_claims),
        },
        "topics": topics,
        "fingerprints": {
            "source_manifest_sha256": _digest(_canonical(manifest)),
            "claim_bindings_sha256": _digest(_canonical(bindings)),
            "comparison_sha256": _digest(_canonical({
                "as_of": as_of, "sources": manifest, "claims": bindings,
            })),
        },
        "content_included": include_content,
    }
    if include_content:
        result["review_claims"] = [{
            "topic_ref": claim["topic_ref"], "source_ref": claim["source_ref"],
            "text_sha256": claim["text_sha256"], "quote_sha256": claim["quote_sha256"],
            "quote": claim["quote"], "currentness": claim["currentness"],
            "span": {"start": claim["start"], "end": claim["end"],
                     "unit": "unicode_code_points", "end_exclusive": True},
            "untrusted_evidence": True, "authority": "none",
            "origin_status": "declared_unverified", "facts_verified": False,
        } for claim in eligible_claims]
    return result
