# ruff: noqa: E501
"""Versioned benchmark dataset loaders for the v1 baseline."""

from __future__ import annotations

from dataclasses import dataclass
from json import loads
from pathlib import Path


@dataclass(frozen=True)
class ScenarioCase:
    """Frozen end-to-end scenario used by the benchmark harness."""

    case_id: str
    intent: str
    content: str
    session_id: str
    mission_id: str | None
    expected_decision: str
    expects_operation: bool
    expects_context_recovery: bool
    expected_domains: list[str]
    required_events: list[str]


@dataclass(frozen=True)
class KnowledgeCase:
    """Frozen retrieval case with expected and forbidden domains."""

    case_id: str
    intent: str
    query: str
    expected_top3: list[str]
    forbidden_domains: list[str]


@dataclass(frozen=True)
class EvolutionTask:
    """Frozen sandbox task for comparing evolution strategies."""

    task_id: str
    proposal_type: str
    target_scope: str
    hypothesis: str
    expected_gain: str
    baseline_metrics: dict[str, float]
    manual_candidate: dict[str, float]
    mipro_candidates: list[dict[str, float]]
    textgrad_candidate: dict[str, float]


@dataclass(frozen=True)
class BenchmarkDataset:
    """Container for the benchmark inputs used across all tracks."""

    scenario_cases: list[ScenarioCase]
    knowledge_cases: list[KnowledgeCase]
    evolution_tasks: list[EvolutionTask]


def load_benchmark_dataset(dataset_path: Path) -> BenchmarkDataset:
    """Load the versioned benchmark dataset from disk."""

    payload = loads(dataset_path.read_text(encoding="utf-8-sig"))
    return BenchmarkDataset(
        scenario_cases=[
            ScenarioCase(
                case_id=item["case_id"],
                intent=item["intent"],
                content=item["content"],
                session_id=item["session_id"],
                mission_id=item.get("mission_id"),
                expected_decision=item["expected_decision"],
                expects_operation=bool(item["expects_operation"]),
                expects_context_recovery=bool(item.get("expects_context_recovery", False)),
                expected_domains=list(item.get("expected_domains", [])),
                required_events=list(item.get("required_events", [])),
            )
            for item in payload.get("scenario_cases", [])
        ],
        knowledge_cases=[
            KnowledgeCase(
                case_id=item["case_id"],
                intent=item["intent"],
                query=item["query"],
                expected_top3=list(item.get("expected_top3", [])),
                forbidden_domains=list(item.get("forbidden_domains", [])),
            )
            for item in payload.get("knowledge_cases", [])
        ],
        evolution_tasks=[
            EvolutionTask(
                task_id=item["task_id"],
                proposal_type=item["proposal_type"],
                target_scope=item["target_scope"],
                hypothesis=item["hypothesis"],
                expected_gain=item["expected_gain"],
                baseline_metrics=dict(item["baseline_metrics"]),
                manual_candidate=dict(item["manual_candidate"]),
                mipro_candidates=[
                    dict(candidate) for candidate in item.get("mipro_candidates", [])
                ],
                textgrad_candidate=dict(item["textgrad_candidate"]),
            )
            for item in payload.get("evolution_tasks", [])
        ],
    )

