"""Persistence layer for local evolution proposals and decisions."""

from __future__ import annotations

from json import dumps, loads
from pathlib import Path
from sqlite3 import Connection, Row, connect

from shared.contracts import EvolutionDecisionContract, EvolutionProposalContract
from shared.types import EvolutionDecisionId, EvolutionProposalId


class EvolutionLabRepository:
    """Persist evolution proposals and decisions in a local sqlite store."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = database_path
        self._initialize()

    def record_proposal(self, proposal: EvolutionProposalContract) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO evolution_proposals (
                    evolution_proposal_id,
                    proposal_type,
                    target_scope,
                    hypothesis,
                    expected_gain,
                    timestamp,
                    source_signals,
                    baseline_refs,
                    risk_hint,
                    requires_sandbox,
                    proposed_tests,
                    promotion_constraints,
                    candidate_refs,
                    refinement_vectors,
                    evaluation_matrix,
                    selection_criteria,
                    strategy_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(proposal.evolution_proposal_id),
                    proposal.proposal_type,
                    proposal.target_scope,
                    proposal.hypothesis,
                    proposal.expected_gain,
                    proposal.timestamp,
                    dumps(proposal.source_signals),
                    dumps(proposal.baseline_refs),
                    proposal.risk_hint,
                    int(proposal.requires_sandbox),
                    dumps(proposal.proposed_tests),
                    dumps(proposal.promotion_constraints),
                    dumps(proposal.candidate_refs),
                    dumps(proposal.refinement_vectors),
                    dumps(proposal.evaluation_matrix),
                    dumps(proposal.selection_criteria),
                    dumps(proposal.strategy_context),
                ),
            )

    def record_decision(self, decision: EvolutionDecisionContract) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO evolution_decisions (
                    evolution_decision_id,
                    evolution_proposal_id,
                    decision,
                    comparison_summary,
                    timestamp,
                    promoted_to,
                    rollback_plan_ref,
                    governance_refs,
                    stability_score,
                    risk_score,
                    notes,
                    baseline_label,
                    candidate_label,
                    selected_candidate_label,
                    selection_criteria,
                    baseline_metrics,
                    candidate_metrics,
                    metric_deltas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(decision.evolution_decision_id),
                    str(decision.evolution_proposal_id),
                    decision.decision,
                    decision.comparison_summary,
                    decision.timestamp,
                    decision.promoted_to,
                    decision.rollback_plan_ref,
                    dumps(decision.governance_refs),
                    decision.stability_score,
                    decision.risk_score,
                    dumps(decision.notes),
                    decision.baseline_label,
                    decision.candidate_label,
                    decision.selected_candidate_label,
                    dumps(decision.selection_criteria),
                    dumps(decision.baseline_metrics),
                    dumps(decision.candidate_metrics),
                    dumps(decision.metric_deltas),
                ),
            )

    def list_proposals(self, limit: int = 20) -> list[EvolutionProposalContract]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM evolution_proposals
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._proposal_from_row(row) for row in rows]

    def list_decisions(self, limit: int = 20) -> list[EvolutionDecisionContract]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM evolution_decisions
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._decision_from_row(row) for row in rows]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS evolution_proposals (
                    evolution_proposal_id TEXT PRIMARY KEY,
                    proposal_type TEXT NOT NULL,
                    target_scope TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    expected_gain TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source_signals TEXT NOT NULL,
                    baseline_refs TEXT NOT NULL,
                    risk_hint TEXT,
                    requires_sandbox INTEGER NOT NULL,
                    proposed_tests TEXT NOT NULL,
                    promotion_constraints TEXT NOT NULL,
                    candidate_refs TEXT NOT NULL DEFAULT '[]',
                    refinement_vectors TEXT NOT NULL DEFAULT '[]',
                    evaluation_matrix TEXT NOT NULL DEFAULT '{}',
                    selection_criteria TEXT NOT NULL DEFAULT '{}',
                    strategy_context TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS evolution_decisions (
                    evolution_decision_id TEXT PRIMARY KEY,
                    evolution_proposal_id TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    comparison_summary TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    promoted_to TEXT,
                    rollback_plan_ref TEXT,
                    governance_refs TEXT NOT NULL,
                    stability_score REAL,
                    risk_score REAL,
                    notes TEXT NOT NULL,
                    baseline_label TEXT,
                    candidate_label TEXT,
                    selected_candidate_label TEXT,
                    selection_criteria TEXT NOT NULL DEFAULT '{}',
                    baseline_metrics TEXT NOT NULL DEFAULT '{}',
                    candidate_metrics TEXT NOT NULL DEFAULT '{}',
                    metric_deltas TEXT NOT NULL DEFAULT '{}'
                );
                """
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "candidate_refs",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "refinement_vectors",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "evaluation_matrix",
                "TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "selection_criteria",
                "TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "strategy_context",
                "TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "baseline_label",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "candidate_label",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "selected_candidate_label",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "selection_criteria",
                "TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "baseline_metrics",
                "TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "candidate_metrics",
                "TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "metric_deltas",
                "TEXT NOT NULL DEFAULT '{}'",
            )

    def _connect(self) -> Connection:
        connection = connect(self.database_path)
        connection.row_factory = Row
        return connection

    @staticmethod
    def _proposal_from_row(row: Row) -> EvolutionProposalContract:
        return EvolutionProposalContract(
            evolution_proposal_id=EvolutionProposalId(row["evolution_proposal_id"]),
            proposal_type=row["proposal_type"],
            target_scope=row["target_scope"],
            hypothesis=row["hypothesis"],
            expected_gain=row["expected_gain"],
            timestamp=row["timestamp"],
            source_signals=loads(row["source_signals"]),
            baseline_refs=loads(row["baseline_refs"]),
            risk_hint=row["risk_hint"],
            requires_sandbox=bool(row["requires_sandbox"]),
            proposed_tests=loads(row["proposed_tests"]),
            promotion_constraints=loads(row["promotion_constraints"]),
            candidate_refs=loads(row["candidate_refs"] or "[]"),
            refinement_vectors=loads(row["refinement_vectors"] or "[]"),
            evaluation_matrix=loads(row["evaluation_matrix"] or "{}"),
            selection_criteria=loads(row["selection_criteria"] or "{}"),
            strategy_context=loads(row["strategy_context"] or "{}"),
        )

    @staticmethod
    def _decision_from_row(row: Row) -> EvolutionDecisionContract:
        return EvolutionDecisionContract(
            evolution_decision_id=EvolutionDecisionId(row["evolution_decision_id"]),
            evolution_proposal_id=EvolutionProposalId(row["evolution_proposal_id"]),
            decision=row["decision"],
            comparison_summary=row["comparison_summary"],
            timestamp=row["timestamp"],
            promoted_to=row["promoted_to"],
            rollback_plan_ref=row["rollback_plan_ref"],
            governance_refs=loads(row["governance_refs"]),
            stability_score=row["stability_score"],
            risk_score=row["risk_score"],
            notes=loads(row["notes"]),
            baseline_label=row["baseline_label"],
            candidate_label=row["candidate_label"],
            selected_candidate_label=row["selected_candidate_label"],
            selection_criteria=loads(row["selection_criteria"] or "{}"),
            baseline_metrics=loads(row["baseline_metrics"] or "{}"),
            candidate_metrics=loads(row["candidate_metrics"] or "{}"),
            metric_deltas=loads(row["metric_deltas"] or "{}"),
        )

    @staticmethod
    def _ensure_column(
        connection: Connection,
        table_name: str,
        column_name: str,
        definition: str,
    ) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in columns:
            return
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )
