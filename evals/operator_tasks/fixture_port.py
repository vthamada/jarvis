"""Positive pipeline control; deterministic parsing is not an intelligent agent."""

from __future__ import annotations

import json
import re
from dataclasses import asdict

from .runner import ExecutionResult


class FixtureTaskPort:
    """Parse only the public synthetic grammar; never use this as model-real evidence."""

    evidence_mode = "fixture"

    def execute(self, request):
        source = request.sources[-1]
        facts, citations = {}, []
        for key in ("quantity", "unit_cost", "shipping", "delivery_day"):
            match = re.search(rf"{key}=([A-Za-z0-9]+)", source.text)
            if match is None:
                return ExecutionResult(request.binding, "incomplete")
            raw = match.group(1)
            facts[key] = int(raw) if raw.isdigit() else raw
            citations.append(
                {
                    "key": key,
                    "source_ref": source.ref,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
        total = facts["quantity"] * facts["unit_cost"] + facts["shipping"]
        kinds = {
            "grounded-report": "report",
            "reviewable-artifact": "artifact",
            "corrected-resumption": "resumption",
        }
        product = {
            "kind": kinds[request.binding.case_id],
            "draft": True,
            "facts": facts,
            "citations": citations,
            "total": total,
        }
        history_digest = ""
        if product["kind"] == "report":
            product["summary"] = "Latest corrected proposal, awaiting budget review."
        elif product["kind"] == "artifact":
            product.update(
                {
                    "filename": "proposal.csv",
                    "media_type": "text/csv",
                    "csv_text": "item,quantity,unit_cost,total\n"
                    f"kits,{facts['quantity']},{facts['unit_cost']},"
                    f"{facts['quantity'] * facts['unit_cost']}\n"
                    f"shipping,1,{facts['shipping']},{facts['shipping']}\n",
                }
            )
        else:
            if request.history is None:
                return ExecutionResult(request.binding, "incomplete")
            product.update(
                {
                    "next_action": "review_budget",
                    "prior_session_ref": request.history.prior_session_ref,
                    "correction_receipt": request.history.correction_receipt,
                }
            )
            history_digest = request.history.digest
        payload = json.dumps(
            {
                "binding": asdict(request.binding),
                "status": "completed",
                "product": product,
            }
        ).encode()
        return ExecutionResult(request.binding, "completed", payload, history_digest)
