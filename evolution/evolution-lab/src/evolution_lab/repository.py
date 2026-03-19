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
                    promotion_constraints
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    promotion_constraints TEXT NOT NULL
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
                    notes TEXT NOT NULL
                );
                """
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
        )
