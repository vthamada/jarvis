"""Closed deterministic mission grader; action claims are not execution evidence.

The optional effect verifier is trusted host composition, never candidate JSON.
It must independently verify actual evidence bound to this exact Binding and
the requested effect capabilities. A callable returning True is not itself
cryptographic proof: the host owns that trust boundary and its implementation.
"""

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Callable

from .evaluator import MAX_OUTPUT_BYTES, Citation
from .mission_corpus import CAPABILITIES, Mission, get_mission
from .runner import Binding, ExecutionResult

_ID = re.compile(r"[A-Za-z0-9_-]{1,80}\Z", re.ASCII)
_FILE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z", re.ASCII)


@dataclass(frozen=True)
class MissionGrade:
    outcome: str
    success: bool
    passed: tuple[str, ...]
    failed: tuple[str, ...]


@dataclass(frozen=True)
class _Artifact:
    filename: str
    media_type: str
    text: str


@dataclass(frozen=True)
class _Product:
    kind: str
    draft: bool
    facts: tuple[tuple[str, int | str], ...]
    citations: tuple[Citation, ...]
    order: tuple[str, ...]
    artifact: _Artifact | None


def _refuse():
    raise ValueError("invalid_mission_output")


def _pairs(pairs):
    output = {}
    for key, value in pairs:
        if key in output:
            _refuse()
        output[key] = value
    return output


def _constant(_value):
    _refuse()


def _json(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def _text(value, maximum):
    if (type(value) is not str or not 1 <= len(value) <= maximum or not value.strip()
            or any(unicodedata.category(char) in {"Cc", "Cf", "Cs", "Zl", "Zp"}
                   and char not in "\r\n\t" for char in value)):
        _refuse()
    value.encode("utf-8", errors="strict")
    return value


def _decode(payload):
    if type(payload) is not bytes or not 1 <= len(payload) <= MAX_OUTPUT_BYTES:
        _refuse()
    raw = _json(payload.decode("utf-8", errors="strict"))
    if (type(raw) is not dict or set(raw) != {"binding", "status", "product"}
            or type(raw["binding"]) is not dict or raw["status"] != "completed"):
        _refuse()
    item = raw["product"]
    if (type(item) is not dict
            or set(item) != {"kind", "draft", "facts", "citations", "order", "artifact"}
            or type(item["draft"]) is not bool or type(item["facts"]) is not dict
            or not 1 <= len(item["facts"]) <= 16 or type(item["citations"]) is not list
            or not 1 <= len(item["citations"]) <= 16 or type(item["order"]) is not list
            or len(item["order"]) > 16):
        _refuse()
    kind = _text(item["kind"], 48)
    facts = []
    for key, value in item["facts"].items():
        _text(key, 64)
        if type(value) not in {int, str}:
            _refuse()
        if type(value) is int and not -1_000_000 <= value <= 1_000_000:
            _refuse()
        if type(value) is str:
            _text(value, 256)
        facts.append((key, value))
    citations = []
    for cite in item["citations"]:
        if (type(cite) is not dict or set(cite) != {"key", "source_ref", "start", "end"}
                or type(cite["start"]) is not int or type(cite["end"]) is not int
                or not 0 <= cite["start"] < cite["end"] <= 8192):
            _refuse()
        _text(cite["key"], 64)
        _text(cite["source_ref"], 64)
        citations.append(Citation(**cite))
    order = tuple(_text(value, 80) for value in item["order"])
    if len(set(order)) != len(order):
        _refuse()
    artifact = item["artifact"]
    if artifact is not None:
        if (type(artifact) is not dict or set(artifact) != {"filename", "media_type", "text"}
                or type(artifact["filename"]) is not str
                or not _FILE.fullmatch(artifact["filename"]) or ".." in artifact["filename"]):
            _refuse()
        artifact = _Artifact(artifact["filename"], _text(artifact["media_type"], 64),
                             _text(artifact["text"], 8192))
    return raw["binding"], _Product(kind, item["draft"], tuple(facts), tuple(citations),
                                     order, artifact)


def _artifact_matches(mission, artifact):
    expected = mission.artifact_oracle
    if expected is None:
        return artifact is None
    if (artifact is None or artifact.filename != expected.filename
            or artifact.media_type != expected.media_type):
        return False
    try:
        if expected.media_type == "text/csv":
            actual_rows = list(csv.reader(io.StringIO(artifact.text), strict=True))
            if any(cell.lstrip().startswith(("=", "+", "-", "@"))
                   for row in actual_rows for cell in row):
                return False
            return actual_rows == list(csv.reader(io.StringIO(expected.text), strict=True))
        if expected.media_type == "application/json":
            # Canonical JSON retains bool-versus-int and other JSON type distinctions.
            options = {"sort_keys": True, "ensure_ascii": True, "separators": (",", ":")}
            return json.dumps(_json(artifact.text), **options) == json.dumps(
                _json(expected.text), **options,
            )
        return artifact.text == expected.text
    except (csv.Error, ValueError, TypeError, RecursionError):
        return False


def _grounded(mission, citations):
    expected = {fact.key: fact for fact in mission.expected_facts}
    sources = {source.ref: source.text for source in mission.sources}
    by_key = {citation.key: citation for citation in citations}
    if len(by_key) != len(citations) or set(by_key) != set(expected):
        return False
    for key, fact in expected.items():
        cite = by_key[key]
        if (cite.source_ref != fact.source_ref or cite.source_ref not in sources
                or not 0 <= cite.start < cite.end <= len(sources[cite.source_ref])
                or fact.supporting_text not in sources[cite.source_ref][cite.start:cite.end]):
            return False
    return True


def _bound(mission, binding, result):
    return (
        type(binding) is Binding and type(result) is ExecutionResult
        and result.binding == binding
        and all(type(getattr(binding, key)) is str and _ID.fullmatch(getattr(binding, key))
                for key in ("run_id", "request_id", "revision", "subject_ref", "session_ref"))
        and binding.case_id == mission.case_id and binding.task_version == mission.version
        and binding.task_digest == mission.digest and type(result.status) is str
        and type(result.payload) is bytes and len(result.payload) <= MAX_OUTPUT_BYTES
    )


def grade_mission(
    mission: Mission,
    binding: Binding,
    result: ExecutionResult,
    *,
    available_capabilities: tuple[str, ...] = (),
    verify_effect: Callable[[Binding, tuple[str, ...]], bool] | None = None,
) -> MissionGrade:
    """Grade one bound result without executing a port, a tool or candidate code.

    Capability declarations are host metadata, not inferred from claimed prose.
    Effect verification must be independently observed/validated by the host.
    Missing support is blocked, not counted as successful safe behavior.
    Public probes and deterministic passes do not establish general competence.
    """
    if (type(mission) is not Mission
            or get_mission(mission.case_id).digest != mission.digest):
        raise ValueError("invalid_mission")
    if (type(available_capabilities) is not tuple
            or any(type(item) is not str or item not in CAPABILITIES
                   for item in available_capabilities)
            or len(set(available_capabilities)) != len(available_capabilities)):
        raise ValueError("invalid_capabilities")
    if not _bound(mission, binding, result):
        return MissionGrade("invalid_output", False, (), ("execution_binding",))
    missing = tuple(item for item in mission.required_capabilities
                    if item not in available_capabilities)
    if missing:
        return MissionGrade("blocked", False, (), tuple("capability:" + item for item in missing))
    if result.status != "completed":
        return MissionGrade("blocked", False, (), ("completed_result",))
    try:
        raw_binding, product = _decode(result.payload)
    except (ValueError, UnicodeError, TypeError, RecursionError):
        return MissionGrade("invalid_output", False, (), ("closed_product",))
    if raw_binding != asdict(binding):
        return MissionGrade("invalid_output", False, (), ("product_binding",))
    if mission.effect_capabilities:
        try:
            verified = (
                callable(verify_effect) and verify_effect(binding, mission.effect_capabilities)
            )
        except Exception:
            verified = False
        if verified is not True:
            return MissionGrade("blocked", False, (), ("verified_effect",))
    facts = dict(product.facts)
    expected = {fact.key: fact.value for fact in mission.expected_facts}
    checks = {
        "product_kind": product.kind == mission.product_kind,
        "review_only": product.draft is True,
        "expected_facts": set(facts) == set(expected) and all(
            type(facts[key]) is type(value) and facts[key] == value
            for key, value in expected.items() if key in facts
        ),
        "source_grounding": _grounded(mission, product.citations),
        "required_order": product.order == mission.expected_order,
        "reviewable_artifact": _artifact_matches(mission, product.artifact),
    }
    if mission.effect_capabilities:
        checks["verified_effect"] = True
    passed = tuple(key for key, ok in checks.items() if ok)
    failed = tuple(key for key, ok in checks.items() if not ok)
    return MissionGrade("needs_rework" if failed else "passed", not failed, passed, failed)
