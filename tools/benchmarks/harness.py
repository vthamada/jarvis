# ruff: noqa: E402,E501
"""Directed local benchmark harness for closing the JARVIS v1 baseline."""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from json import dumps
from math import log
from os import getenv
from pathlib import Path
from re import findall
from tempfile import gettempdir
from time import perf_counter
from typing import Callable
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
SRC_DIRS = [
    ROOT,
    ROOT / "evolution" / "evolution-lab" / "src",
    ROOT / "services" / "orchestrator-service" / "src",
    ROOT / "services" / "memory-service" / "src",
    ROOT / "services" / "governance-service" / "src",
    ROOT / "services" / "operational-service" / "src",
    ROOT / "services" / "knowledge-service" / "src",
    ROOT / "services" / "observability-service" / "src",
    ROOT / "engines" / "identity-engine" / "src",
    ROOT / "engines" / "executive-engine" / "src",
    ROOT / "engines" / "cognitive-engine" / "src",
    ROOT / "engines" / "planning-engine" / "src",
    ROOT / "engines" / "synthesis-engine" / "src",
    ROOT / "engines" / "specialist-engine" / "src",
]

for src_dir in SRC_DIRS:
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

from evolution_lab.service import ComparisonInput, EvolutionLabService
from knowledge_service.service import KnowledgeService
from memory_service.repository import normalize_database_url
from memory_service.service import MemoryService
from observability_service.service import ObservabilityQuery, ObservabilityService
from operational_service.service import OperationalService
from orchestrator_service.service import OrchestratorService

from shared.contracts import InputContract
from shared.types import ChannelType, InputType, MissionId, RequestId, SessionId
from tools.benchmarks.dataset import (
    BenchmarkDataset,
    EvolutionTask,
    KnowledgeCase,
    load_benchmark_dataset,
)

ADOPT_IN_V1 = "adotar no v1"
MAINTAIN_BASELINE = "manter baseline atual"
DEFER_TO_V2 = "deferir para v2"
DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "v1_benchmark_cases.json"
DEFAULT_OUTPUT_DIR = Path.cwd() / ".jarvis_runtime" / "benchmarks"
RECORD_LATENCY_THRESHOLD_MS = 150.0
FETCH_LATENCY_THRESHOLD_MS = 150.0
LATENCY_MULTIPLIER = 12.0


@dataclass(frozen=True)
class TrackReport:
    """Normalized output for a single benchmark track."""

    name: str
    decision: str
    metrics: dict[str, object]
    notes: list[str]


@dataclass(frozen=True)
class BenchmarkRunReport:
    """Structured result of a full benchmark harness execution."""

    run_id: str
    generated_at: str
    dataset_path: str
    output_directory: str
    tracks: dict[str, TrackReport]
    json_report_path: str
    markdown_report_path: str

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the report."""

        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "dataset_path": self.dataset_path,
            "output_directory": self.output_directory,
            "json_report_path": self.json_report_path,
            "markdown_report_path": self.markdown_report_path,
            "tracks": {name: asdict(report) for name, report in self.tracks.items()},
        }


class NullObservabilityService:
    """No-op observability sink used to estimate ingest overhead."""

    def ingest_events(self, events: list[object]) -> None:
        _ = events


class BenchmarkHarness:
    """Run directed benchmarks against the current v1 baseline."""

    def __init__(
        self,
        dataset_path: str | None = None,
        output_dir: str | None = None,
        postgres_url: str | None = None,
    ) -> None:
        resolved_dataset = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
        self.dataset_path = resolved_dataset
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.dataset: BenchmarkDataset = load_benchmark_dataset(self.dataset_path)
        self.postgres_url = normalize_database_url(postgres_url or getenv("DATABASE_URL"))
        self.run_id = f"bench-{uuid4().hex[:8]}"

    def run(self) -> BenchmarkRunReport:
        """Execute all benchmark tracks and persist auditable artifacts."""

        tracks = {
            "memory": self.run_memory_track(),
            "knowledge": self.run_knowledge_track(),
            "observability": self.run_observability_track(),
            "evolution": self.run_evolution_track(),
        }
        generated_at = self.now()
        json_report_path = self.output_dir / f"{self.run_id}.json"
        markdown_report_path = self.output_dir / f"{self.run_id}.md"
        report = BenchmarkRunReport(
            run_id=self.run_id,
            generated_at=generated_at,
            dataset_path=str(self.dataset_path),
            output_directory=str(self.output_dir),
            tracks=tracks,
            json_report_path=str(json_report_path),
            markdown_report_path=str(markdown_report_path),
        )
        json_report_path.write_text(dumps(report.as_dict(), indent=2), encoding="utf-8")
        markdown_report_path.write_text(self._render_markdown_report(report), encoding="utf-8")
        return report

    def run_memory_track(self) -> TrackReport:
        """Compare the current sqlite backend with optional PostgreSQL persistence."""

        sqlite_runtime = self._runtime_dir("benchmark-memory-sqlite")
        sqlite_url = f"sqlite:///{(sqlite_runtime / 'memory.db').as_posix()}"
        baseline = self._exercise_memory_backend("sqlite", sqlite_url)

        notes = [
            "Baseline fixo: sqlite local do memory-service.",
            "Paridade funcional e persistencia entre instancias sao obrigatorias para adocao.",
        ]
        if self.postgres_url:
            candidate = self._exercise_memory_backend("postgresql", self.postgres_url)
            notes.append("Candidate principal avaliada com DATABASE_URL configurada.")
        else:
            candidate = {
                "backend": "postgresql",
                "executed": False,
                "functional_parity": False,
                "persistence_across_instances": False,
                "mission_state_persisted": False,
                "failure_rate": 1.0,
                "average_record_latency_ms": None,
                "average_fetch_latency_ms": None,
                "operational_simplicity": 0.0,
                "notes": [
                    "DATABASE_URL nao configurada; benchmark de PostgreSQL nao executado.",
                    "Use infra/local-postgres.compose.yml para validar a candidata operacional do v1.",
                ],
            }
            notes.extend(candidate["notes"])

        decision = MAINTAIN_BASELINE
        if candidate.get("executed"):
            sqlite_record = float(baseline["average_record_latency_ms"])
            sqlite_fetch = float(baseline["average_fetch_latency_ms"])
            candidate_record = float(candidate["average_record_latency_ms"])
            candidate_fetch = float(candidate["average_fetch_latency_ms"])
            candidate_is_viable = (
                bool(candidate["functional_parity"])
                and bool(candidate["persistence_across_instances"])
                and bool(candidate["mission_state_persisted"])
                and float(candidate["failure_rate"]) == 0.0
                and float(candidate["operational_simplicity"]) >= 0.5
                and candidate_record <= max(sqlite_record * LATENCY_MULTIPLIER, RECORD_LATENCY_THRESHOLD_MS)
                and candidate_fetch <= max(sqlite_fetch * LATENCY_MULTIPLIER, FETCH_LATENCY_THRESHOLD_MS)
            )
            if candidate_is_viable:
                decision = ADOPT_IN_V1
                notes.append("PostgreSQL atende a regra de adocao operacional do v1.")
            else:
                notes.append("PostgreSQL ainda nao superou os criterios minimos de adocao do v1.")

        return TrackReport(
            name="memory",
            decision=decision,
            metrics={
                "baseline": baseline,
                "candidate": candidate,
            },
            notes=notes,
        )

    def run_knowledge_track(self) -> TrackReport:
        """Benchmark deterministic retrieval candidates against the current baseline."""

        service = KnowledgeService()
        knowledge_cases = self.dataset.knowledge_cases
        baseline = self._evaluate_knowledge_strategy(
            "baseline_deterministic",
            lambda intent, query: (
                service.retrieve_for_intent(intent=intent, query=query).active_domains
            ),
            knowledge_cases,
        )
        weighted = self._evaluate_knowledge_strategy(
            "weighted_deterministic",
            lambda intent, query: self._weighted_rank_domains(intent, query, service),
            knowledge_cases,
        )
        lexical = self._evaluate_knowledge_strategy(
            "lexical_bm25_like",
            lambda intent, query: self._lexical_rank_domains(intent, query, service),
            knowledge_cases,
        )

        decision = MAINTAIN_BASELINE
        selected_candidate = "baseline_deterministic"
        notes = [
            "Benchmark local, deterministico e sem servicos externos.",
            "Vector DB, embeddings online e reranker externo seguem fora do escopo do v1.",
        ]

        weighted_gain = float(weighted["top3_relevance"]) - float(baseline["top3_relevance"])
        lexical_gain = float(lexical["top3_relevance"]) - float(baseline["top3_relevance"])
        if (
            weighted_gain >= 0.08
            and bool(weighted["deterministic"])
            and float(weighted["false_positive_rate"]) <= float(baseline["false_positive_rate"])
        ):
            decision = ADOPT_IN_V1
            selected_candidate = "weighted_deterministic"
            notes.append(
                "Ranking deterministico com pesos explicitos melhorou relevancia sem perder previsibilidade."
            )
        elif (
            lexical_gain >= 0.08
            and bool(lexical["deterministic"])
            and float(lexical["false_positive_rate"]) <= float(baseline["false_positive_rate"])
        ):
            decision = ADOPT_IN_V1
            selected_candidate = "lexical_bm25_like"
            notes.append(
                "Scorer lexical local melhora relevancia sem depender de infraestrutura externa."
            )
        else:
            notes.append("Nenhuma candidata superou o baseline com ganho material suficiente.")

        return TrackReport(
            name="knowledge",
            decision=decision,
            metrics={
                "selected_candidate": selected_candidate,
                "baseline": baseline,
                "weighted_candidate": weighted,
                "lexical_candidate": lexical,
            },
            notes=notes,
        )

    def run_observability_track(self) -> TrackReport:
        """Validate whether the current event trail is sufficient for controlled production."""

        runtime_without_observability = self._runtime_dir("benchmark-observability-null")
        runtime_with_observability = self._runtime_dir("benchmark-observability-real")
        baseline_without_ingest = self._execute_observability_flow(
            runtime_without_observability,
            NullObservabilityService(),
        )
        observed_metrics = self._execute_observability_flow(runtime_with_observability, None)

        completeness = float(observed_metrics["trail_completeness"])
        reconstructability = float(observed_metrics["reconstructability"])
        query_quality = float(observed_metrics["query_quality"])
        export_compatibility = float(observed_metrics["trace_export_compatibility"])
        overhead = max(
            0.0,
            float(observed_metrics["average_latency_ms"])
            - float(baseline_without_ingest["average_latency_ms"]),
        )

        decision = MAINTAIN_BASELINE
        notes = [
            "A trilha interna continua sendo a fonte canonica de auditoria do v1.",
            "Camadas externas de tracing entram apenas como complemento, nunca como dependencia central.",
        ]
        if (
            completeness == 1.0
            and reconstructability == 1.0
            and query_quality == 1.0
            and export_compatibility == 1.0
        ):
            decision = ADOPT_IN_V1
            notes.append(
                "A trilha observavel atual ja atende os criterios minimos do v1 controlado."
            )
        else:
            notes.append("Ainda ha lacunas de cobertura ou reconstrucao na trilha observavel.")

        return TrackReport(
            name="observability",
            decision=decision,
            metrics={
                **observed_metrics,
                "ingest_overhead_ms": round(overhead, 4),
                "baseline_without_ingest": baseline_without_ingest,
            },
            notes=notes,
        )

    def run_evolution_track(self) -> TrackReport:
        """Compare sandbox-only evolution strategies over a frozen task set."""

        runtime = self._runtime_dir("benchmark-evolution")
        algorithms = {
            "manual_variants": self._manual_candidate_from_task,
            "mipro_like_search": self._mipro_candidate_from_task,
            "textgrad_like_refinement": self._textgrad_candidate_from_task,
        }
        summaries = {
            name: self._evaluate_evolution_algorithm(name, selector, runtime / name)
            for name, selector in algorithms.items()
        }

        baseline_risk = round(
            sum(task.baseline_metrics["risk"] for task in self.dataset.evolution_tasks)
            / len(self.dataset.evolution_tasks),
            4,
        )
        decision = DEFER_TO_V2
        selected_algorithm = "none"
        notes = [
            "Todas as candidatas permanecem sandbox-only e sem promocao automatica.",
            "A saida esperada do v1 e um laboratorio evolutivo mais serio, nao autoevolucao em runtime.",
        ]

        for candidate_name in ("manual_variants", "mipro_like_search", "textgrad_like_refinement"):
            candidate = summaries[candidate_name]
            if (
                float(candidate["success_rate"]) >= 0.66
                and float(candidate["average_risk"]) <= baseline_risk
                and float(candidate["average_cost_relative"]) <= 1.15
                and float(candidate["average_latency_relative"]) <= 1.1
                and float(candidate["decision_stability"]) == 1.0
            ):
                decision = ADOPT_IN_V1
                selected_algorithm = candidate_name
                notes.append(
                    f"{candidate_name} atende o corte de incorporacao no evolution-lab do v1."
                )
                break

        if decision != ADOPT_IN_V1:
            notes.append(
                "Nenhuma candidata atingiu o corte minimo sem aumentar risco ou custo alem do aceitavel."
            )

        return TrackReport(
            name="evolution",
            decision=decision,
            metrics={
                "selected_algorithm": selected_algorithm,
                "baseline_average_risk": baseline_risk,
                "algorithms": summaries,
            },
            notes=notes,
        )

    def _exercise_memory_backend(self, backend_label: str, database_url: str) -> dict[str, object]:
        """Run the functional and latency checks for a memory backend."""

        failures = 0
        scope_id = uuid4().hex[:8]
        record_latencies: list[float] = []
        fetch_latencies: list[float] = []
        persistence_ok = False
        functional_parity = False
        mission_state_ok = False
        notes: list[str] = []
        try:
            for iteration in range(3):
                contract = InputContract(
                    request_id=RequestId(f"{backend_label}-{scope_id}-req-{iteration}"),
                    session_id=SessionId(f"{backend_label}-{scope_id}-session"),
                    mission_id=MissionId(f"{backend_label}-{scope_id}-mission"),
                    channel=ChannelType.CHAT,
                    input_type=InputType.TEXT,
                    content=f"Plan benchmark iteration {iteration}.",
                    timestamp=f"2026-03-19T00:00:0{iteration}Z",
                )
                writer = MemoryService(database_url=database_url)
                start = perf_counter()
                writer.record_turn(contract, intent="planning", response_text="Benchmark response.")
                record_latencies.append((perf_counter() - start) * 1000)

                reader = MemoryService(database_url=database_url)
                start = perf_counter()
                recovered = reader.recover_for_input(contract)
                fetch_latencies.append((perf_counter() - start) * 1000)

                if iteration == 2:
                    persistence_ok = any(
                        "Benchmark response." in item for item in recovered.recovered_items
                    )
                    mission_state = reader.get_mission_state(f"{backend_label}-{scope_id}-mission")
                    mission_state_ok = (
                        mission_state is not None and "planning" in mission_state.active_tasks
                    )
                    functional_parity = any(
                        ("context_summary=" in item)
                        or ("Benchmark response." in item)
                        or ("intent=planning" in item)
                        for item in recovered.recovered_items
                    )
        except Exception as exc:  # pragma: no cover - exercised only in unsupported envs.
            failures += 1
            notes.append(f"backend_error={exc}")

        simplicity = 1.0 if backend_label == "sqlite" else 0.7
        return {
            "backend": backend_label,
            "executed": failures == 0,
            "functional_parity": functional_parity,
            "persistence_across_instances": persistence_ok,
            "mission_state_persisted": mission_state_ok,
            "failure_rate": round(failures / 3, 4),
            "average_record_latency_ms": round(sum(record_latencies) / len(record_latencies), 4)
            if record_latencies
            else None,
            "average_fetch_latency_ms": round(sum(fetch_latencies) / len(fetch_latencies), 4)
            if fetch_latencies
            else None,
            "operational_simplicity": simplicity,
            "notes": notes,
        }

    def _evaluate_knowledge_strategy(
        self,
        strategy_name: str,
        strategy: Callable[[str, str], list[str]],
        knowledge_cases: list[KnowledgeCase],
    ) -> dict[str, object]:
        """Measure retrieval relevance, determinism, and local latency."""

        case_results: list[dict[str, object]] = []
        latencies: list[float] = []
        false_positives = 0
        deterministic = True
        relevance_total = 0.0

        for case in knowledge_cases:
            repeated_outputs: list[list[str]] = []
            for _ in range(3):
                start = perf_counter()
                ranked_domains = strategy(case.intent, case.query)
                latencies.append((perf_counter() - start) * 1000)
                repeated_outputs.append(list(ranked_domains[:3]))
            predicted = repeated_outputs[0]
            deterministic = deterministic and all(
                output == predicted for output in repeated_outputs[1:]
            )
            case_relevance = self._ranked_relevance(predicted, case.expected_top3)
            relevance_total += case_relevance
            has_false_positive = any(domain in predicted for domain in case.forbidden_domains)
            false_positives += int(has_false_positive)
            case_results.append(
                {
                    "case_id": case.case_id,
                    "predicted_top3": predicted,
                    "expected_top3": case.expected_top3,
                    "relevance": round(case_relevance, 4),
                    "false_positive": has_false_positive,
                }
            )

        total_cases = max(len(knowledge_cases), 1)
        return {
            "strategy": strategy_name,
            "top3_relevance": round(relevance_total / total_cases, 4),
            "false_positive_rate": round(false_positives / total_cases, 4),
            "deterministic": deterministic,
            "average_latency_ms": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
            "cases": case_results,
        }

    def _weighted_rank_domains(
        self,
        intent: str,
        query: str,
        service: KnowledgeService,
    ) -> list[str]:
        """Candidate 1: weighted deterministic ranking over the local corpus."""

        intent_prior = {
            "planning": {"strategy": 3.0, "productivity": 2.0},
            "analysis": {"analysis": 3.0, "strategy": 2.0},
            "general_assistance": {"productivity": 2.0},
        }
        lowered = query.lower()
        scores: dict[str, float] = {}
        for domain_name, domain in service.domains.items():
            score = intent_prior.get(intent, {}).get(domain_name, 0.0)
            score += 1.6 if domain_name in lowered else 0.0
            score += sum(1.25 for keyword in domain.keywords if keyword in lowered)
            if "audit" in lowered and domain_name == "governance":
                score += 1.5
            scores[domain_name] = score
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        filtered = [name for name, score in ranked if score > 0.0]
        return filtered[:3] or ["productivity"]

    def _lexical_rank_domains(
        self,
        intent: str,
        query: str,
        service: KnowledgeService,
    ) -> list[str]:
        """Candidate 2: lexical local scorer inspired by BM25."""

        query_tokens = self._tokenize(query)
        documents = {
            name: self._tokenize(" ".join([name, *domain.keywords, *domain.snippets]))
            for name, domain in service.domains.items()
        }
        average_document_length = sum(len(tokens) for tokens in documents.values()) / max(
            len(documents), 1
        )
        scores: dict[str, float] = {}
        for domain_name, tokens in documents.items():
            token_count = len(tokens) or 1
            score = 0.0
            for term in query_tokens:
                tf = tokens.count(term)
                if tf == 0:
                    continue
                doc_frequency = sum(1 for document in documents.values() if term in document)
                idf = log((len(documents) - doc_frequency + 0.5) / (doc_frequency + 0.5) + 1.0)
                k1 = 1.2
                b = 0.75
                score += idf * (
                    (tf * (k1 + 1))
                    / (tf + k1 * (1 - b + b * (token_count / average_document_length)))
                )
            if intent == "planning" and domain_name in {"strategy", "productivity"}:
                score += 0.3
            if intent == "analysis" and domain_name in {"analysis", "strategy"}:
                score += 0.3
            scores[domain_name] = score
        ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        filtered = [name for name, score in ranked if score > 0.0]
        return filtered[:3] or ["productivity"]

    def _execute_observability_flow(
        self,
        runtime_dir: Path,
        null_observability: NullObservabilityService | None,
    ) -> dict[str, object]:
        """Execute the frozen scenarios and measure observability sufficiency."""

        memory_url = f"sqlite:///{(runtime_dir / 'memory.db').as_posix()}"
        operational = OperationalService(artifact_dir=str(runtime_dir / "artifacts"))
        observability = (
            null_observability
            if null_observability is not None
            else ObservabilityService(database_path=str(runtime_dir / "observability.db"))
        )
        service = OrchestratorService(
            memory_service=MemoryService(database_url=memory_url),
            operational_service=operational,
            observability_service=observability,
        )

        coverage_scores: list[float] = []
        reconstruction_scores: list[float] = []
        query_scores: list[float] = []
        export_scores: list[float] = []
        latencies: list[float] = []

        for index, scenario in enumerate(self.dataset.scenario_cases):
            request_id = f"bench-req-{index + 1}"
            contract = InputContract(
                request_id=RequestId(request_id),
                session_id=SessionId(scenario.session_id),
                mission_id=MissionId(scenario.mission_id) if scenario.mission_id else None,
                channel=ChannelType.CHAT,
                input_type=InputType.TEXT,
                content=scenario.content,
                timestamp=f"2026-03-19T00:00:0{index}Z",
            )
            start = perf_counter()
            response = service.handle_input(contract)
            latencies.append((perf_counter() - start) * 1000)

            if null_observability is not None:
                continue

            assert isinstance(observability, ObservabilityService)
            request_events = observability.list_recent_events(
                ObservabilityQuery(request_id=request_id)
            )
            present_event_names = [event.event_name for event in request_events]
            required = scenario.required_events
            coverage_scores.append(
                round(
                    sum(1 for event_name in required if event_name in present_event_names)
                    / max(len(required), 1),
                    4,
                )
            )
            reconstruction_scores.append(
                1.0
                if present_event_names == [event.event_name for event in response.events]
                else 0.0
            )

            query_hits = [
                len(observability.list_recent_events(ObservabilityQuery(request_id=request_id)))
                > 0,
                len(
                    observability.list_recent_events(
                        ObservabilityQuery(session_id=scenario.session_id)
                    )
                )
                > 0,
                len(observability.list_recent_events(ObservabilityQuery(correlation_id=request_id)))
                > 0,
            ]
            if scenario.mission_id:
                query_hits.append(
                    len(
                        observability.list_recent_events(
                            ObservabilityQuery(mission_id=scenario.mission_id)
                        )
                    )
                    > 0
                )
            query_scores.append(sum(1 for hit in query_hits if hit) / len(query_hits))

            trace_view = observability.export_trace_view(ObservabilityQuery(request_id=request_id))
            export_scores.append(
                1.0 if len(trace_view) == len(request_events) and trace_view else 0.0
            )

        if null_observability is not None:
            return {
                "average_latency_ms": round(sum(latencies) / len(latencies), 4)
                if latencies
                else 0.0,
                "trail_completeness": 0.0,
                "reconstructability": 0.0,
                "query_quality": 0.0,
                "trace_export_compatibility": 0.0,
            }

        return {
            "average_latency_ms": round(sum(latencies) / len(latencies), 4) if latencies else 0.0,
            "trail_completeness": round(sum(coverage_scores) / len(coverage_scores), 4)
            if coverage_scores
            else 0.0,
            "reconstructability": round(sum(reconstruction_scores) / len(reconstruction_scores), 4)
            if reconstruction_scores
            else 0.0,
            "query_quality": round(sum(query_scores) / len(query_scores), 4)
            if query_scores
            else 0.0,
            "trace_export_compatibility": round(sum(export_scores) / len(export_scores), 4)
            if export_scores
            else 0.0,
        }

    def _evaluate_evolution_algorithm(
        self,
        algorithm_name: str,
        selector: Callable[[EvolutionTask], dict[str, float]],
        runtime_dir: Path,
    ) -> dict[str, object]:
        """Run a frozen sandbox evaluation for a candidate evolution strategy."""

        runtime_dir.mkdir(parents=True, exist_ok=True)
        service = EvolutionLabService(database_path=str(runtime_dir / "evolution.db"))
        sandbox_successes = 0
        risk_values: list[float] = []
        cost_relative_values: list[float] = []
        latency_relative_values: list[float] = []
        decision_stability_checks: list[float] = []

        for task in self.dataset.evolution_tasks:
            round_decisions: list[str] = []
            candidate_metrics = selector(task)
            baseline_metrics = self._comparison_metrics(task.baseline_metrics)
            comparison_candidate_metrics = self._comparison_metrics(candidate_metrics)
            for round_index in range(3):
                proposal = service.create_proposal(
                    proposal_type=task.proposal_type,
                    target_scope=task.target_scope,
                    hypothesis=task.hypothesis,
                    expected_gain=task.expected_gain,
                    baseline_refs=[f"benchmark://{task.task_id}/baseline"],
                    source_signals=[f"benchmark://{algorithm_name}/round-{round_index + 1}"],
                    proposed_tests=["pytest -q", "python -m tools.benchmarks"],
                )
                result = service.compare_candidate(
                    proposal,
                    ComparisonInput(
                        baseline_label="baseline",
                        candidate_label=algorithm_name,
                        baseline_metrics=baseline_metrics,
                        candidate_metrics=comparison_candidate_metrics,
                        governance_refs=["policy://sandbox/manual-review"],
                        notes=[f"task_id={task.task_id}", f"algorithm={algorithm_name}"],
                    ),
                )
                round_decisions.append(result.decision.decision)
            sandbox_successes += int(
                all(decision == "sandbox_candidate" for decision in round_decisions)
            )
            decision_stability_checks.append(1.0 if len(set(round_decisions)) == 1 else 0.0)
            risk_values.append(float(candidate_metrics["risk"]))
            cost_relative_values.append(
                round(float(candidate_metrics["cost"]) / float(task.baseline_metrics["cost"]), 4)
            )
            latency_relative_values.append(
                round(
                    float(candidate_metrics["latency"]) / float(task.baseline_metrics["latency"]), 4
                )
            )

        total_tasks = max(len(self.dataset.evolution_tasks), 1)
        return {
            "success_rate": round(sandbox_successes / total_tasks, 4),
            "decision_stability": round(
                sum(decision_stability_checks) / len(decision_stability_checks), 4
            ),
            "average_risk": round(sum(risk_values) / len(risk_values), 4),
            "average_cost_relative": round(
                sum(cost_relative_values) / len(cost_relative_values), 4
            ),
            "average_latency_relative": round(
                sum(latency_relative_values) / len(latency_relative_values), 4
            ),
        }

    @staticmethod
    def _manual_candidate_from_task(task: EvolutionTask) -> dict[str, float]:
        """Return the frozen manual candidate profile for a task."""

        return dict(task.manual_candidate)

    @staticmethod
    def _mipro_candidate_from_task(task: EvolutionTask) -> dict[str, float]:
        """Pick the best local search candidate using a simple utility score."""

        scored = sorted(
            task.mipro_candidates,
            key=lambda candidate: (
                candidate["success"]
                + candidate["stability"]
                + candidate["throughput"]
                - candidate["risk"]
                - (candidate["cost"] - 1.0)
                - (candidate["latency"] - 1.0)
            ),
            reverse=True,
        )
        chosen = dict(scored[0]) if scored else dict(task.manual_candidate)
        chosen.pop("label", None)
        return chosen

    @staticmethod
    def _textgrad_candidate_from_task(task: EvolutionTask) -> dict[str, float]:
        """Return the frozen offline refinement candidate profile."""

        return dict(task.textgrad_candidate)

    @staticmethod
    def _comparison_metrics(metrics: dict[str, float]) -> dict[str, float]:
        """Select the metrics that participate in sandbox comparison decisions."""

        return {
            "success": float(metrics["success"]),
            "stability": float(metrics["stability"]),
            "throughput": float(metrics["throughput"]),
            "risk": float(metrics["risk"]),
        }

    @staticmethod
    def _ranked_relevance(predicted: list[str], expected: list[str]) -> float:
        """Compute a relevance score that rewards both presence and ranking order."""

        if not expected:
            return 1.0
        weights = [1.0, 0.6, 0.3]
        expected_top = expected[:3]
        predicted_top = predicted[:3]
        ideal = sum(weight * weight for weight in weights[: len(expected_top)])
        score = 0.0
        for predicted_index, domain in enumerate(predicted_top):
            if domain in expected_top:
                expected_index = expected_top.index(domain)
                score += weights[predicted_index] * weights[expected_index]
        return score / ideal if ideal else 0.0

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Split text into deterministic lowercase tokens."""

        return findall(r"[a-z0-9_]+", text.lower())

    @staticmethod
    def _runtime_dir(name: str) -> Path:
        """Create an isolated runtime directory for a benchmark track."""

        base_dir = Path(gettempdir()) / "jarvis-benchmarks"
        base_dir.mkdir(parents=True, exist_ok=True)
        target = base_dir / f"{name}-{uuid4().hex[:8]}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _render_markdown_report(self, report: BenchmarkRunReport) -> str:
        """Render a short markdown summary for human review."""

        lines = [
            "# Benchmark Report",
            "",
            f"- Run ID: `{report.run_id}`",
            f"- Generated at: `{report.generated_at}`",
            f"- Dataset: `{report.dataset_path}`",
            "",
        ]
        for track_name, track in report.tracks.items():
            lines.extend(
                [
                    f"## {track_name.title()}",
                    "",
                    f"- Decision: `{track.decision}`",
                    f"- Notes: {' | '.join(track.notes)}",
                    "",
                    "```json",
                    dumps(track.metrics, indent=2),
                    "```",
                    "",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def now() -> str:
        """Return the current UTC timestamp."""

        return datetime.now(UTC).isoformat()


def build_cli_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the benchmark harness."""

    parser = argparse.ArgumentParser(description="Run the JARVIS v1 local benchmark harness.")
    parser.add_argument(
        "--dataset-path",
        dest="dataset_path",
        default=None,
        help="Override the default benchmark dataset path.",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        help="Directory for benchmark JSON and Markdown artifacts.",
    )
    parser.add_argument(
        "--postgres-url",
        dest="postgres_url",
        default=None,
        help="Explicit PostgreSQL DATABASE_URL for the memory track.",
    )
    parser.add_argument(
        "--print-json",
        dest="print_json",
        action="store_true",
        help="Print the full JSON report payload to stdout after execution.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the benchmark harness and print the output artifact locations."""

    args = build_cli_parser().parse_args(argv)
    report = BenchmarkHarness(
        dataset_path=args.dataset_path,
        output_dir=args.output_dir,
        postgres_url=args.postgres_url,
    ).run()
    print(report.json_report_path)
    print(report.markdown_report_path)
    if args.print_json:
        print(dumps(report.as_dict(), indent=2))
    return 0

