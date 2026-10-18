"""Public diversity, immutable grading metadata and unchanged v1 compatibility."""

import json
from collections import Counter
from dataclasses import FrozenInstanceError, asdict, replace

import pytest

from evals.operator_tasks import corpus as v1
from evals.operator_tasks.mission_corpus import (
    CAPABILITIES,
    CORPUS_DIGEST,
    DATA_LABEL,
    MISSIONS,
    VERSION,
    get_mission,
)
from evals.operator_tasks.runner import Binding, ExecutionRequest


def test_twenty_five_diverse_missions_with_public_dev_probe_splits():
    assert len(MISSIONS) == len({mission.case_id for mission in MISSIONS}) == 25
    assert Counter(mission.category for mission in MISSIONS) == {
        "report_research": 5, "data_artifact": 4, "prioritization": 3,
        "memory_correction": 3, "browser": 3, "code": 3, "integration": 2, "resumption": 2,
    }
    assert Counter(mission.split for mission in MISSIONS) == {"dev": 16, "probe": 9}
    assert len({mission.digest for mission in MISSIONS}) == 25
    assert all(mission.version == VERSION == "operator-missions-v1" for mission in MISSIONS)
    assert len(CORPUS_DIGEST) == 64 and set(CORPUS_DIGEST) <= set("0123456789abcdef")


@pytest.mark.parametrize("mission", MISSIONS, ids=lambda item: item.case_id)
def test_sources_and_oracles_are_authored_bounded_consistent_and_labeled(mission):
    assert mission.brief.startswith(DATA_LABEL)
    assert "no secret holdout" in " ".join(mission.review_limits)
    assert mission.sources and all(source.text.startswith(DATA_LABEL) for source in mission.sources)
    sources = {source.ref: source.text for source in mission.sources}
    assert len(sources) == len(mission.sources)
    assert all(len(source.ref) <= 64 and len(source.text) <= 8192 for source in mission.sources)
    assert 2 <= len(mission.expected_facts) <= 16
    assert len({fact.key for fact in mission.expected_facts}) == len(mission.expected_facts)
    assert all(fact.source_ref in sources and fact.supporting_text in sources[fact.source_ref]
               for fact in mission.expected_facts)
    assert set(mission.required_capabilities) <= CAPABILITIES
    assert set(mission.effect_capabilities) <= set(mission.required_capabilities)
    assert len(set(mission.required_capabilities)) == len(mission.required_capabilities)
    assert f"kind='{mission.product_kind}'" in mission.brief


def test_real_effects_are_explicit_not_inferred_from_a_category_or_text_claim():
    assert {mission.case_id for mission in MISSIONS if mission.effect_capabilities} == {
        "memory-canonical-recall", "browser-open-hours", "browser-multistep-navigation",
        "code-run-tests", "integration-read-status", "resume-canonical-recovery",
    }
    assert get_mission("code-review-boundary").effect_capabilities == ()
    assert get_mission("code-patch-draft").effect_capabilities == ()
    assert get_mission("browser-form-draft").effect_capabilities == ()
    assert get_mission("resume-uncertain-dispatch").effect_capabilities == ()


def test_frozen_catalog_and_oracles_cannot_be_replaced_by_candidate_metadata():
    mission = MISSIONS[0]
    with pytest.raises(FrozenInstanceError):
        mission.brief = "candidate-chosen question"
    with pytest.raises(FrozenInstanceError):
        mission.sources[0].text = "candidate-chosen evidence"
    with pytest.raises(FrozenInstanceError):
        mission.expected_facts[0].value = "candidate-chosen answer"
    artifact = get_mission("data-expense-csv").artifact_oracle
    with pytest.raises(FrozenInstanceError):
        artifact.text = "candidate-chosen artifact"
    assert replace(mission, split="probe").digest != mission.digest


def test_execution_request_reuses_v1_without_oracles_or_grading_metadata():
    mission = get_mission("data-expense-csv")
    binding = Binding("run", "request", mission.case_id, mission.version, mission.digest,
                      "rev", "subject", "session")
    request = ExecutionRequest(binding, mission.brief, mission.sources, 60.0, None)
    assert set(asdict(request)) == {"binding", "brief", "sources", "deadline", "history"}
    assert request.sources is mission.sources and request.history is None
    serialized = json.dumps(asdict(request))
    assert "expected_facts" not in serialized and "artifact_oracle" not in serialized
    assert "supporting_text" not in serialized and "review_limits" not in serialized


def test_v1_corpus_digest_and_existing_task_catalog_remain_exactly_unchanged():
    assert v1.VERSION == "operator-tasks-v1"
    assert tuple(task.case_id for task in v1.TASKS) == (
        "grounded-report", "reviewable-artifact", "corrected-resumption",
    )
    assert v1.CORPUS_DIGEST == "c70a17581da807f404e92b518dd3393a8b618a5ee20d694f07ac394e5261ed46"


def test_unknown_mission_is_not_silently_substituted():
    with pytest.raises(ValueError, match="^unknown_mission$"):
        get_mission("not-a-public-mission")
