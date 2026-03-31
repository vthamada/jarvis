"""Render local baseline evidence for the v2 memory gap evidence cut."""

from __future__ import annotations

from json import loads
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = (
    ROOT / "tools" / "benchmarks" / "datasets" / "v2_memory_gap_baseline_scope_rules.json"
)
OUTPUT_PATH = ROOT / "docs" / "implementation" / "v2-memory-gap-baseline-evidence.md"
CONTRACTS_PATH = ROOT / "shared" / "contracts" / "__init__.py"
SERVICE_PATH = (
    ROOT / "services" / "memory-service" / "src" / "memory_service" / "service.py"
)
REPOSITORY_PATH = (
    ROOT / "services" / "memory-service" / "src" / "memory_service" / "repository.py"
)
REGISTRY_PATH = ROOT / "shared" / "memory_registry.py"


def load_dataset() -> dict[str, object]:
    return loads(DATASET_PATH.read_text(encoding="utf-8-sig"))


def load_sources() -> dict[str, str]:
    return {
        "contracts": CONTRACTS_PATH.read_text(encoding="utf-8"),
        "service": SERVICE_PATH.read_text(encoding="utf-8"),
        "repository": REPOSITORY_PATH.read_text(encoding="utf-8"),
        "registry": REGISTRY_PATH.read_text(encoding="utf-8"),
    }


def evaluate_scope(
    scope: dict[str, object],
    sources: dict[str, str],
) -> dict[str, object]:
    rules = []
    all_rules_match = True
    for rule in scope["rules"]:
        source_key = str(rule["source"])
        snippet = str(rule["snippet"])
        expected_present = bool(rule["expected_present"])
        actual_present = snippet in sources[source_key]
        matched = actual_present == expected_present
        all_rules_match = all_rules_match and matched
        rules.append(
            {
                "rule_id": rule["rule_id"],
                "source": source_key,
                "expected_present": expected_present,
                "actual_present": actual_present,
                "matched": matched,
                "reason": rule["reason"],
            }
        )

    if all_rules_match:
        status = scope["status_when_rules_match"]
        gap_read = scope["gap_read_when_rules_match"]
    else:
        status = "inconsistent"
        gap_read = "needs_manual_review"

    return {
        "scope_id": scope["scope_id"],
        "title": scope["title"],
        "status": status,
        "gap_read": gap_read,
        "supports_hypotheses": list(scope["supports_hypotheses"]),
        "baseline_read": list(scope["baseline_read"]),
        "rules": rules,
        "matched_rule_count": sum(1 for item in rules if item["matched"]),
        "rule_count": len(rules),
    }


def build_hypothesis_reads(scopes: list[dict[str, object]]) -> list[dict[str, object]]:
    hypothesis_map: dict[str, list[dict[str, object]]] = {}
    for scope in scopes:
        for hypothesis_id in scope["supports_hypotheses"]:
            hypothesis_map.setdefault(hypothesis_id, []).append(scope)

    reads = []
    for hypothesis_id, related_scopes in sorted(hypothesis_map.items()):
        gap_reads = {scope["gap_read"] for scope in related_scopes}
        if "partial_gap_supported" in gap_reads:
            evidence_state = "supported_by_baseline_read"
        elif "not_proven_gap" in gap_reads:
            evidence_state = "not_yet_proven"
        else:
            evidence_state = "baseline_sufficient_now"
        reads.append(
            {
                "hypothesis_id": hypothesis_id,
                "evidence_state": evidence_state,
                "supporting_scopes": [scope["scope_id"] for scope in related_scopes],
            }
        )
    return reads


def build_payload() -> dict[str, object]:
    dataset = load_dataset()
    sources = load_sources()
    scopes = [evaluate_scope(scope, sources) for scope in dataset["scopes"]]
    hypothesis_reads = build_hypothesis_reads(scopes)
    scope_totals = {
        "implemented": sum(1 for scope in scopes if scope["status"] == "implemented"),
        "typed_tracking_only": sum(
            1 for scope in scopes if scope["status"] == "typed_tracking_only"
        ),
        "core_mediated_handoff_only": sum(
            1 for scope in scopes if scope["status"] == "core_mediated_handoff_only"
        ),
        "future_shape_only": sum(
            1 for scope in scopes if scope["status"] == "future_shape_only"
        ),
        "inconsistent": sum(1 for scope in scopes if scope["status"] == "inconsistent"),
    }
    overall_decision = "hold_mem0_as_conditional_candidate"
    if scope_totals["inconsistent"] > 0:
        overall_decision = "evidence_requires_manual_review"
    return {
        "cut_id": dataset["cut_id"],
        "sprint_id": dataset["sprint_id"],
        "scope_count": len(scopes),
        "scope_totals": scope_totals,
        "overall_decision": overall_decision,
        "scopes": scopes,
        "hypothesis_reads": hypothesis_reads,
    }


def render_markdown(payload: dict[str, object]) -> str:
    lines = [
        "# V2 Memory Gap Baseline Evidence",
        "",
        f"- cut: `{payload['cut_id']}`",
        f"- sprint: `{payload['sprint_id']}`",
        f"- scope_count: `{payload['scope_count']}`",
        f"- overall_decision: `{payload['overall_decision']}`",
        "",
        "## Summary",
        "",
        f"- implemented scopes: `{payload['scope_totals']['implemented']}`",
        (
            "- typed tracking only scopes: "
            f"`{payload['scope_totals']['typed_tracking_only']}`"
        ),
        (
            "- core mediated handoff only scopes: "
            f"`{payload['scope_totals']['core_mediated_handoff_only']}`"
        ),
        (
            "- future shape only scopes: "
            f"`{payload['scope_totals']['future_shape_only']}`"
        ),
        f"- inconsistent scopes: `{payload['scope_totals']['inconsistent']}`",
        "",
    ]
    for scope in payload["scopes"]:
        lines.extend(
            [
                f"## {scope['title']}",
                "",
                f"- scope_id: `{scope['scope_id']}`",
                f"- status: `{scope['status']}`",
                f"- gap_read: `{scope['gap_read']}`",
                "- baseline_read:",
            ]
        )
        for item in scope["baseline_read"]:
            lines.append(f"  - {item}")
        lines.append("- rule_evidence:")
        for rule in scope["rules"]:
            expectation = "present" if rule["expected_present"] else "absent"
            actual = "present" if rule["actual_present"] else "absent"
            lines.append(
                "  - "
                f"`{rule['rule_id']}` from `{rule['source']}`: expected `{expectation}`, "
                f"found `{actual}`; {rule['reason']}"
            )
        if scope["supports_hypotheses"]:
            lines.append("- supports_hypotheses:")
            for hypothesis_id in scope["supports_hypotheses"]:
                lines.append(f"  - `{hypothesis_id}`")
        lines.append("")

    lines.extend(["## Hypothesis Read", ""])
    for item in payload["hypothesis_reads"]:
        lines.append(f"### {item['hypothesis_id']}")
        lines.append("")
        lines.append(f"- evidence_state: `{item['evidence_state']}`")
        lines.append("- supporting_scopes:")
        for scope_id in item["supporting_scopes"]:
            lines.append(f"  - `{scope_id}`")
        lines.append("")

    lines.extend(
        [
            "## Current Read",
            "",
            "- conversation, session and mission scopes are already operational in the baseline;",
            (
                "- user scope is typed and tracked, but still not runtime rich enough "
                "to count as a stronger layer;"
            ),
            (
                "- specialist shared memory is strong for handoff, but it still does not "
                "prove a stronger persistent agent scope;"
            ),
            "- organization scope remains a future shape and is not yet a proven baseline failure;",
            (
                "- the current read supports `Mem0` staying as `absorver_depois`, not as a "
                "reopen-ready dependency."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUTPUT_PATH.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    print(
        "rendered="
        f"{OUTPUT_PATH.relative_to(ROOT)} scopes={payload['scope_count']} "
        f"decision={payload['overall_decision']}"
    )


if __name__ == "__main__":
    main()
