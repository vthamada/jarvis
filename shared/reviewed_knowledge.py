"""Request-scoped reviewed text data; never authentication, a grant or verified fact.

Separate from InputContract.content and Knowledge snippets: remote instructions
must not become Executive input, a planning rationale or specialist instructions.
No I/O, provider, corpus mutation, registry or parallel memory lives here.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from urllib.parse import urlsplit

MAX_SOURCE_BYTES = 16384
MAX_QUERY_CHARACTERS = 2048
MAX_QUOTE_CHARACTERS = 512
REVIEWED_EVIDENCE_MARKER = (
    "Reviewed source excerpt (untrusted, declared provenance; not verified facts "
    "or action confirmations):\n"
)
GENERATIVE_ANALYSIS_MARKER = (
    "Model-generated analysis (unverified; not facts, grants or action confirmations):\n"
)
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z", re.ASCII)
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


def _text(value, maximum):
    if (type(value) is not str or not 1 <= len(value) <= maximum or not value.strip()
            or any(unicodedata.category(char) in {"Cc", "Cf", "Cs"}
                   and char not in "\r\n\t" for char in value)):
        raise ValueError("invalid_reviewed_knowledge")
    return value


def _timestamp(value):
    if type(value) is not str or len(value) > 64 or not _STAMP.fullmatch(value):
        raise ValueError("invalid_reviewed_knowledge")
    return datetime.fromisoformat(value).astimezone(UTC)


def _url(value):
    if (type(value) is not str or not 1 <= len(value) <= 4096 or not value.isascii()
            or any(ord(char) <= 32 or ord(char) == 127 for char in value)
            or "\\" in value or "#" in value):
        raise ValueError("invalid_reviewed_knowledge")
    parsed = urlsplit(value)
    host = parsed.hostname
    if (not host or len(host) > 253 or len(host.split(".")) < 2
            or not re.search(r"[a-z]", host.rsplit(".", 1)[-1])
            or any(not _LABEL.fullmatch(label) for label in host.split("."))
            or parsed.scheme != "https" or parsed.netloc != host
            or not parsed.path.startswith("/") or parsed.fragment
            or parsed.username is not None or parsed.password is not None
            or parsed.port is not None):
        raise ValueError("invalid_reviewed_knowledge")
    target = parsed.path + ("?" + parsed.query if parsed.query else "")
    if (value != f"https://{host}{target}" or re.search(r"%(?![0-9A-F]{2})", target)
            or re.search(r"[^A-Za-z0-9._~:/?@!$&'()*+,;=%-]", target)):
        raise ValueError("invalid_reviewed_knowledge")


@dataclass(frozen=True, slots=True)
class KnowledgeReviewBinding:
    principal_ref: str = field(repr=False)
    session_id: str = field(repr=False)
    request_id: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ReviewedTextSource:
    text: str = field(repr=False)
    source_url: str = field(repr=False)
    observed_at: str
    content_sha256: str = field(repr=False)
    byte_count: int
    media_type: str
    expires_at: str | None = None

    @property
    def source_ref(self) -> str:
        # A consistency fingerprint, not authentication or anonymization.
        values = [getattr(self, item.name) for item in fields(self) if item.name != "text"]
        raw = json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        return "provided:sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ReviewedKnowledgeContext:
    binding: KnowledgeReviewBinding = field(repr=False)
    query: str = field(repr=False)
    source: ReviewedTextSource = field(repr=False)
    start: int
    end: int
    quote: str = field(repr=False)
    reviewed_at: str
    revision: int
    authority: str = "none"
    origin_status: str = "declared_unverified"


def validate_binding(value):
    if type(value) is not KnowledgeReviewBinding:
        raise ValueError("invalid_reviewed_knowledge")
    values = tuple(getattr(value, item.name) for item in fields(value))
    if any(type(item) is not str or not _REF.fullmatch(item) for item in values):
        raise ValueError("invalid_reviewed_knowledge")
    return KnowledgeReviewBinding(*values)


def validate_source(value, *, as_of=None):
    try:
        if type(value) is not ReviewedTextSource:
            raise ValueError()
        data = {item.name: getattr(value, item.name) for item in fields(value)}
        source = ReviewedTextSource(**data)
        raw = _text(source.text, MAX_SOURCE_BYTES).encode("utf-8", errors="strict")
        if (type(source.byte_count) is not int or source.byte_count != len(raw)
                or not 1 <= len(raw) <= MAX_SOURCE_BYTES
                or type(source.content_sha256) is not str
                or not _HASH.fullmatch(source.content_sha256)
                or source.content_sha256 != hashlib.sha256(raw).hexdigest()
                or type(source.media_type) is not str
                or source.media_type not in {"text/plain", "text/html"}):
            raise ValueError()
        _url(source.source_url)
        observed = _timestamp(source.observed_at)
        expiry = _timestamp(source.expires_at) if source.expires_at is not None else None
        if expiry is not None and expiry < observed:
            raise ValueError()
        if as_of is not None:
            now = _timestamp(as_of)
            if observed > now or (expiry is not None and now >= expiry):
                raise ValueError()
        return source
    except Exception:
        raise ValueError("invalid_reviewed_knowledge") from None


def validate_context(value, *, binding=None, query=None, as_of=None):
    try:
        if type(value) is not ReviewedKnowledgeContext:
            raise ValueError()
        data = {item.name: getattr(value, item.name) for item in fields(value)}
        data["binding"] = validate_binding(data["binding"])
        data["source"] = validate_source(data["source"], as_of=as_of)
        context = ReviewedKnowledgeContext(**data)
        _text(context.query, MAX_QUERY_CHARACTERS)
        _text(context.quote, MAX_QUOTE_CHARACTERS)
        if (type(context.start) is not int or type(context.end) is not int
                or not 0 <= context.start < context.end <= len(context.source.text)
                or context.source.text[context.start:context.end] != context.quote
                or type(context.revision) is not int or not 1 <= context.revision <= 2**31 - 1
                or type(context.authority) is not str or context.authority != "none"
                or type(context.origin_status) is not str
                or context.origin_status != "declared_unverified"):
            raise ValueError()
        reviewed = _timestamp(context.reviewed_at)
        if reviewed < _timestamp(context.source.observed_at):
            raise ValueError()
        if as_of is not None and reviewed > _timestamp(as_of):
            raise ValueError()
        if binding is not None and context.binding != validate_binding(binding):
            raise ValueError()
        if query is not None and (type(query) is not str or context.query != query):
            raise ValueError()
        return context
    except Exception:
        raise ValueError("invalid_reviewed_knowledge") from None


def context_fingerprint(value):
    context = validate_context(value)
    data = [context.binding.principal_ref, context.binding.session_id,
            context.binding.request_id, context.query, context.source.source_ref,
            context.start, context.end, context.quote, context.reviewed_at, context.revision,
            context.authority, context.origin_status]
    return hashlib.sha256(json.dumps(data, ensure_ascii=True).encode("ascii")).hexdigest()


def render_reviewed_evidence(value):
    context = validate_context(value)
    encoded = json.dumps(context.quote, ensure_ascii=True)
    quoted = "".join(f"\\u{ord(char):04x}" if char in "[]()!*_~#:/<>&`" else char
                     for char in encoded)
    return (REVIEWED_EVIDENCE_MARKER
            + f"{context.source.source_ref} [{context.start}:{context.end}] {quoted}")


def response_for_planning(value: str) -> str:
    """Project a retained final without reusing its literal untrusted attachment.

    This is a read-side view, not deletion/redaction of the canonical turn. The
    marker belongs to the sovereign renderer; the source itself is JSON escaped
    and cannot close the appended section. Ambiguous marked tails are withheld.
    """
    boundaries = [
        (value.find(marker), marker)
        for marker in (REVIEWED_EVIDENCE_MARKER, GENERATIVE_ANALYSIS_MARKER)
        if marker in value
    ]
    if not boundaries:
        return value
    offset, marker = min(boundaries)
    description = ("source excerpt" if marker == REVIEWED_EVIDENCE_MARKER
                   else "model analysis")
    return (value[:offset].rstrip()
            + f"\n\n[Prior untrusted {description} withheld from planning context.]")
