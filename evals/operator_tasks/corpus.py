"""Immutable public task corpus; expected facts never travel to a candidate port."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

VERSION = "operator-tasks-v1"


@dataclass(frozen=True)
class Source:
    ref: str
    text: str


@dataclass(frozen=True)
class Fact:
    key: str
    value: int | str
    source_ref: str
    supporting_text: str


@dataclass(frozen=True)
class Task:
    case_id: str
    product_kind: str
    brief: str
    sources: tuple[Source, ...]
    expected: tuple[Fact, ...]
    version: str = VERSION

    @property
    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


INITIAL = Source(
    "purchase-rev1",
    "Public synthetic workshop purchase. quantity=40; unit_cost=18; shipping=60; "
    "delivery_day=Wednesday. This is a proposal, not authorization to spend.",
)
CORRECTION = Source(
    "correction-rev2",
    "Correction revision 2 supersedes revision 1: quantity=30; unit_cost=18; "
    "shipping=60; delivery_day=Thursday. Review the budget before purchasing.",
)
FACTS = (
    Fact("quantity", 30, CORRECTION.ref, "quantity=30"),
    Fact("unit_cost", 18, CORRECTION.ref, "unit_cost=18"),
    Fact("shipping", 60, CORRECTION.ref, "shipping=60"),
    Fact("delivery_day", "Thursday", CORRECTION.ref, "delivery_day=Thursday"),
)
TASKS = (
    Task(
        "grounded-report",
        "report",
        "Write a concise purchase report using the latest correction. Return a JSON report "
        "with a free-form summary, all four facts and contiguous source spans for every fact. "
        "Calculate the total as quantity * unit_cost + shipping. Mark it as a draft. "
        "No purchase or tool execution is authorized.",
        (INITIAL, CORRECTION),
        FACTS,
    ),
    Task(
        "reviewable-artifact",
        "artifact",
        "Produce a reviewable proposal.csv, not a file-system write. Return a JSON artifact "
        "with media_type=text/csv and CSV text. Columns: item,quantity,unit_cost,total. "
        "Include kits and shipping rows using the latest source; the shipping quantity is 1. "
        "Return total and source citations for all four facts. Mark it as a draft. "
        "Do not purchase, execute formulas, or create files.",
        (INITIAL, CORRECTION),
        FACTS,
    ),
    Task(
        "corrected-resumption",
        "resumption",
        "Resume the corrected proposal in a different session of the same synthetic subject. "
        "Return JSON corrected state with all four facts, source spans, total, "
        "next_action=review_budget, prior_session_ref and correction_receipt from the supplied "
        "trusted history. Mark it as a draft. Do not substitute the superseded initial values.",
        (INITIAL, CORRECTION),
        FACTS,
    ),
)
CORPUS_DIGEST = hashlib.sha256("".join(task.digest for task in TASKS).encode()).hexdigest()


def get_task(case_id: str) -> Task:
    for task in TASKS:
        if task.case_id == case_id:
            return task
    raise ValueError("unknown_case")
