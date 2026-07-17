from dataclasses import replace

from shared.contract_validation import validate_contract_instance
from shared.schemas import DOMAIN_EVAL_PACK_SCHEMA, DOMAIN_EVAL_RUN_SCHEMA
from tools.domain_eval_support import (
    DEFAULT_DOMAIN_EVAL_PACK_PATH,
    load_domain_eval_pack,
    run_domain_eval_pack,
    validate_domain_eval_pack,
)


def test_analysis_domain_eval_pack_matches_promoted_route() -> None:
    pack = load_domain_eval_pack()

    assert DEFAULT_DOMAIN_EVAL_PACK_PATH.exists()
    assert pack.route_name == "analysis"
    assert pack.workflow_profile == "structured_analysis_workflow"
    assert pack.specialist_type == "structured_analysis_specialist"
    assert len(pack.cases) == 2
    assert validate_domain_eval_pack(pack) == []
    assert validate_contract_instance(pack, schema=DOMAIN_EVAL_PACK_SCHEMA).status == "coherent"


def test_domain_eval_pack_blocks_non_promoted_or_mutating_candidate(tmp_path) -> None:
    pack = load_domain_eval_pack()
    invalid = replace(
        pack,
        route_name="documentation",
        automatic_promotion_allowed=True,
        core_mutation_allowed=True,
    )

    blockers = validate_domain_eval_pack(invalid)

    assert "route_not_promoted_for_governed_eval" in blockers
    assert "automatic_promotion_requested" in blockers
    assert "core_mutation_requested" in blockers


def test_domain_eval_pack_runs_route_response_memory_and_specialist_end_to_end(tmp_path) -> None:
    result = run_domain_eval_pack(
        workdir=tmp_path / "domain-eval",
        run_id="domain-eval-test",
        generated_at="2026-07-16T00:00:00Z",
    )

    assert result.status == "passed"
    assert result.readiness_status == "candidate_ready_for_human_review"
    assert result.promotion_readiness == "manual_review_only"
    assert result.pass_rate == 1.0
    assert result.total_cases == 2
    assert result.promotion_authorized is False
    assert result.automatic_promotion_allowed is False
    assert result.core_mutation_allowed is False
    assert validate_contract_instance(result, schema=DOMAIN_EVAL_RUN_SCHEMA).status == "coherent"
    seed, followup = result.case_results
    assert seed.observed_route == "analysis"
    assert seed.observed_workflow_profile == "structured_analysis_workflow"
    assert "structured_analysis_specialist" in seed.observed_specialist_types
    assert followup.observed_memory_causality_status == "causal_guidance"
    assert all(case.checks["response"] for case in result.case_results)
    assert all(case.checks["required_events"] for case in result.case_results)


def test_domain_eval_failure_is_observable_and_blocks_readiness(tmp_path) -> None:
    pack = load_domain_eval_pack()
    broken_case = replace(
        pack.cases[0],
        required_response_fragments=["fragment-that-cannot-exist-in-output"],
    )
    broken_pack = replace(pack, cases=[broken_case])
    pack_path = tmp_path / "broken-pack.json"
    from dataclasses import asdict
    from json import dumps

    pack_path.write_text(dumps(asdict(broken_pack)), encoding="utf-8")
    result = run_domain_eval_pack(
        pack_path=pack_path,
        workdir=tmp_path / "broken-run",
        run_id="domain-eval-broken",
        generated_at="2026-07-16T00:00:00Z",
    )

    assert result.status == "failed"
    assert result.readiness_status == "attention_required"
    assert result.promotion_readiness == "blocked"
    assert "case:analysis_seed:response_mismatch" in result.blockers
