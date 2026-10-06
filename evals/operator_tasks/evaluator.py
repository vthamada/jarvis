"""Independent product evaluator, not a model-selected grader or prose matcher."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass

from .corpus import Task

MAX_OUTPUT_BYTES = 16384


@dataclass(frozen=True)
class Citation:
    key: str
    source_ref: str
    start: int
    end: int


@dataclass(frozen=True)
class Product:
    kind: str
    draft: bool
    facts: tuple[tuple[str, int | str], ...]
    citations: tuple[Citation, ...]
    total: int
    summary: str = ""
    filename: str = ""
    media_type: str = ""
    csv_text: str = ""
    next_action: str = ""
    prior_session_ref: str = ""
    correction_receipt: str = ""


@dataclass(frozen=True)
class Score:
    passed: tuple[str, ...]
    failed: tuple[str, ...]

    @property
    def success(self) -> bool:
        return not self.failed

    @property
    def fraction(self) -> float:
        return len(self.passed) / (len(self.passed) + len(self.failed))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def _text(value, *, limit=2048):
    if (
        type(value) is not str
        or not 1 <= len(value) <= limit
        or not value.strip()
        or any(ord(c) < 32 and c not in "\n\r\t" for c in value)
        or any(0xD800 <= ord(c) <= 0xDFFF for c in value)
    ):
        raise ValueError("invalid_text")
    return value


def decode_product(payload: bytes) -> tuple[dict, Product]:
    """Strict bounded JSON shape: no score, evaluator, arbitrary fields or attachments."""
    if type(payload) is not bytes or not 1 <= len(payload) <= MAX_OUTPUT_BYTES:
        raise ValueError("invalid_payload")
    try:
        raw = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_number")),
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid_json") from exc
    if type(raw) is not dict or set(raw) != {"binding", "status", "product"}:
        raise ValueError("invalid_envelope")
    if raw["status"] != "completed" or type(raw["binding"]) is not dict:
        raise ValueError("incomplete_output")
    value = raw["product"]
    base = {"kind", "draft", "facts", "citations", "total"}
    extra = {
        "report": {"summary"},
        "artifact": {"filename", "media_type", "csv_text"},
        "resumption": {"next_action", "prior_session_ref", "correction_receipt"},
    }
    if (
        type(value) is not dict
        or type(value.get("kind")) is not str
        or value["kind"] not in extra
        or set(value) != base | extra[value["kind"]]
        or type(value["draft"]) is not bool
        or type(value["total"]) is not int
        or not 0 <= value["total"] <= 1000000
        or type(value["facts"]) is not dict
        or not 1 <= len(value["facts"]) <= 8
        or type(value["citations"]) is not list
        or not 1 <= len(value["citations"]) <= 8
    ):
        raise ValueError("invalid_product")
    facts = []
    for key, fact in value["facts"].items():
        _text(key, limit=64)
        if type(fact) not in (int, str):
            raise ValueError("invalid_fact")
        if type(fact) is int and not 0 <= fact <= 1000000:
            raise ValueError("invalid_fact")
        if type(fact) is str:
            _text(fact, limit=128)
        facts.append((key, fact))
    citations = []
    for item in value["citations"]:
        if type(item) is not dict or set(item) != {"key", "source_ref", "start", "end"}:
            raise ValueError("invalid_citation")
        _text(item["key"], limit=64)
        _text(item["source_ref"], limit=64)
        if (
            type(item["start"]) is not int
            or type(item["end"]) is not int
            or not 0 <= item["start"] < item["end"] <= 8192
        ):
            raise ValueError("invalid_citation")
        citations.append(Citation(**item))
    kwargs = {key: _text(value[key]) for key in extra[value["kind"]]}
    return raw["binding"], Product(
        value["kind"], value["draft"], tuple(facts), tuple(citations), value["total"], **kwargs
    )


def score_product(
    task: Task,
    product: Product,
    *,
    prior_session_ref: str = "",
    correction_receipt: str = "",
    history_verified: bool = False,
) -> Score:
    """Evaluate facts, source grounding, arithmetic, reviewability and correction binding.

    Narrative style and broad reasoning quality remain human-review questions.
    Trusted composition must validate the output envelope before invoking this function.
    """
    facts = dict(product.facts)
    checks = {
        "product_kind": product.kind == task.product_kind,
        "review_only": product.draft is True,
        "latest_facts": facts == {fact.key: fact.value for fact in task.expected},
        "arithmetic": product.total == 30 * 18 + 60,
    }
    sources = {source.ref: source.text for source in task.sources}
    expected = {fact.key: fact for fact in task.expected}
    citations = {cite.key: cite for cite in product.citations}
    grounding = len(citations) == len(product.citations) and set(citations) == set(expected)
    for key, fact in expected.items():
        cite = citations.get(key)
        grounding = grounding and bool(
            cite
            and cite.source_ref == fact.source_ref
            and 0 <= cite.start < cite.end <= len(sources[fact.source_ref])
            and fact.supporting_text in sources[fact.source_ref][cite.start : cite.end]
        )
    checks["source_grounding"] = bool(grounding)
    if task.product_kind == "report":
        checks["readable_summary"] = bool(product.summary.strip())
    elif task.product_kind == "artifact":
        checks["reviewable_csv"] = _reviewable_csv(product)
    else:
        checks["correction_continuity"] = (
            history_verified
            and bool(prior_session_ref and correction_receipt)
            and product.prior_session_ref == prior_session_ref
            and product.correction_receipt == correction_receipt
            and product.next_action == "review_budget"
        )
    return Score(
        tuple(key for key, ok in checks.items() if ok),
        tuple(key for key, ok in checks.items() if not ok),
    )


def _reviewable_csv(product: Product) -> bool:
    if product.filename != "proposal.csv" or product.media_type != "text/csv":
        return False
    try:
        reader = csv.DictReader(io.StringIO(product.csv_text), strict=True)
        if reader.fieldnames != ["item", "quantity", "unit_cost", "total"]:
            return False
        rows = list(reader)
        if len(rows) != 2 or any(None in row or None in row.values() for row in rows):
            return False
        actual = {}
        for row in rows:
            if row["item"] in actual:
                return False
            cells = [row[key] for key in ("quantity", "unit_cost", "total")]
            if any(not cell.isascii() or not cell.isdigit() or len(cell) > 7 for cell in cells):
                return False
            quantity, cost, total = map(int, cells)
            if quantity * cost != total:
                return False
            actual[row["item"]] = (quantity, cost, total)
        return actual == {"kits": (30, 18, 540), "shipping": (1, 60, 60)}
    except (csv.Error, ValueError):
        return False
