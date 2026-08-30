"""Persistence layer for local evolution proposals and decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from json import dumps, loads
from pathlib import Path
from sqlite3 import Connection, Row, connect

from shared.contracts import (
    EvolutionDecisionContract,
    EvolutionProposalContract,
    TechnologyExperimentCaseContract,
    TechnologyExperimentCaseResultContract,
    TechnologyExperimentControlSnapshotContract,
    TechnologyExperimentEvalRunClaimContract,
    TechnologyExperimentEvalRunContract,
    TechnologyExperimentObservationContract,
    TechnologyExperimentPackContract,
    TechnologyRadarIntakeContract,
    WorkflowVariantEvalCaseContract,
    WorkflowVariantEvalCasePackContract,
    WorkflowVariantEvalCaseResultContract,
    WorkflowVariantEvalControlSnapshotContract,
    WorkflowVariantEvalObservationContract,
    WorkflowVariantEvalRunContract,
)
from shared.technology_experiment import (
    canonical_technology_experiment_payload,
    require_valid_technology_experiment_eval_run,
    require_valid_technology_experiment_pack,
    technology_experiment_artifact_fingerprint,
    technology_experiment_eval_run_fingerprint,
    technology_experiment_pack_fingerprint,
    validate_technology_experiment_eval_run_claim,
)
from shared.technology_radar_intake import (
    canonical_technology_radar_intake_payload,
    require_valid_technology_radar_intake,
    technology_radar_intake_fingerprint,
    technology_radar_source_identity,
)
from shared.types import EvolutionDecisionId, EvolutionProposalId
from shared.versioning import parse_canonical_semver
from shared.workflow_variant_eval import (
    canonical_workflow_variant_eval_payload,
    validate_workflow_variant_eval_case_pack,
    validate_workflow_variant_eval_run,
    workflow_variant_eval_control_fingerprint,
    workflow_variant_eval_fingerprint,
)


@dataclass(frozen=True)
class WorkflowVariantEvalRunClaim:
    """Immutable reservation of one controlled evaluation identity."""

    run_id: str
    input_fingerprint: str
    baseline_version_ref: str
    baseline_definition_hash: str
    candidate_version_ref: str
    candidate_definition_hash: str
    case_pack_id: str
    case_pack_version: str
    case_pack_fingerprint: str
    control_fingerprint: str
    claimed_at: str


def workflow_variant_eval_pack_input_fingerprint(
    case_pack: WorkflowVariantEvalCasePackContract,
) -> str:
    payload = dumps(
        [
            {
                "case_id": case.case_id,
                "case_version": case.case_version,
                "input_snapshot_fingerprint": case.input_snapshot_fingerprint,
            }
            for case in case_pack.cases
        ],
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def workflow_variant_eval_pack_control_fingerprint(
    case_pack: WorkflowVariantEvalCasePackContract,
) -> str:
    payload = dumps(
        [
            {
                "case_id": case.case_id,
                "case_version": case.case_version,
                "control_fingerprint": workflow_variant_eval_control_fingerprint(
                    case.control_snapshot
                ),
            }
            for case in case_pack.cases
        ],
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


class EvolutionLabRepository:
    """Persist evolution proposals and decisions in a local sqlite store."""

    def __init__(self, database_path: Path, *, read_only: bool = False) -> None:
        self.database_path = database_path
        self.read_only = read_only
        if not self.read_only:
            database_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize()

    def record_proposal(self, proposal: EvolutionProposalContract) -> None:
        self._ensure_writable()
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
                    optimization_scope,
                    optimization_target_kind,
                    optimization_candidate_status,
                    optimization_safety_status,
                    optimization_blockers,
                    candidate_refs,
                    refinement_vectors,
                    evaluation_matrix,
                    selection_criteria,
                    strategy_context
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    proposal.optimization_scope,
                    proposal.optimization_target_kind,
                    proposal.optimization_candidate_status,
                    proposal.optimization_safety_status,
                    dumps(proposal.optimization_blockers),
                    dumps(proposal.candidate_refs),
                    dumps(proposal.refinement_vectors),
                    dumps(proposal.evaluation_matrix),
                    dumps(proposal.selection_criteria),
                    dumps(proposal.strategy_context),
                ),
            )

    def record_decision(self, decision: EvolutionDecisionContract) -> None:
        self._ensure_writable()
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
                    optimization_scope,
                    optimization_target_kind,
                    optimization_readiness,
                    optimization_release_status,
                    optimization_safety_status,
                    optimization_blockers,
                    baseline_label,
                    candidate_label,
                    selected_candidate_label,
                    selection_criteria,
                    baseline_metrics,
                    candidate_metrics,
                    metric_deltas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    decision.optimization_scope,
                    decision.optimization_target_kind,
                    decision.optimization_readiness,
                    decision.optimization_release_status,
                    decision.optimization_safety_status,
                    dumps(decision.optimization_blockers),
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

    def fetch_proposal(
        self,
        evolution_proposal_id: str,
    ) -> EvolutionProposalContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM evolution_proposals
                WHERE evolution_proposal_id = ?
                """,
                (evolution_proposal_id,),
            ).fetchone()
        return None if row is None else self._proposal_from_row(row)

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

    def record_workflow_lifecycle_release_bundle(
        self,
        *,
        transition_id: str,
        workflow_profile: str,
        route: str,
        revision: int,
        transition_action: str,
        bundle: dict[str, object],
    ) -> dict[str, object]:
        """Append the exact release evidence used to build one transition."""

        self._ensure_writable()
        payload = dumps(
            bundle,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        payload_sha256 = sha256(payload.encode("utf-8")).hexdigest()
        values = (
            transition_id,
            workflow_profile,
            route,
            revision,
            transition_action,
            payload,
            payload_sha256,
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO workflow_lifecycle_release_bundles (
                    transition_id,
                    workflow_profile,
                    route,
                    revision,
                    transition_action,
                    payload,
                    payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            if cursor.rowcount == 1:
                return bundle
            rows = connection.execute(
                """
                SELECT *
                FROM workflow_lifecycle_release_bundles
                WHERE transition_id = ?
                   OR (workflow_profile = ? AND route = ? AND revision = ?)
                """,
                (transition_id, workflow_profile, route, revision),
            ).fetchall()
        if len(rows) != 1 or self._workflow_lifecycle_release_bundle_row_values(
            rows[0]
        ) != values:
            raise ValueError(
                "workflow lifecycle release bundle identity collision"
            )
        return bundle

    def fetch_workflow_lifecycle_release_bundle(
        self,
        transition_id: str,
    ) -> dict[str, object] | None:
        """Return a hash-verified release bundle, failing closed on tamper."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM workflow_lifecycle_release_bundles
                WHERE transition_id = ?
                """,
                (transition_id,),
            ).fetchone()
        return self._verified_workflow_lifecycle_release_bundle_from_row(row)

    def register_workflow_variant_case_pack(
        self,
        case_pack: WorkflowVariantEvalCasePackContract,
    ) -> WorkflowVariantEvalCasePackContract:
        """Append an immutable case pack, accepting only an exact retry."""

        self._ensure_writable()
        payload = canonical_workflow_variant_eval_payload(case_pack)
        payload_sha256 = workflow_variant_eval_fingerprint(case_pack)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO workflow_eval_case_packs (
                    case_pack_id,
                    case_pack_version,
                    workflow_profile,
                    route,
                    baseline_version_ref,
                    candidate_version_ref,
                    generated_at,
                    payload,
                    payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case_pack.case_pack_id,
                    case_pack.case_pack_version,
                    case_pack.workflow_profile,
                    case_pack.route,
                    case_pack.baseline_version_ref,
                    case_pack.candidate_version_ref,
                    str(case_pack.generated_at),
                    payload,
                    payload_sha256,
                ),
            )
            row = connection.execute(
                """
                SELECT *
                FROM workflow_eval_case_packs
                WHERE case_pack_id = ? AND case_pack_version = ?
                """,
                (case_pack.case_pack_id, case_pack.case_pack_version),
            ).fetchone()
            connection.commit()
        if cursor.rowcount == 1:
            return case_pack
        existing = self._verified_case_pack_from_row(row)
        if existing is None:
            raise ValueError("stored workflow variant case pack failed integrity verification")
        if (
            str(row["payload"]) != payload
            or str(row["payload_sha256"]) != payload_sha256
        ):
            raise ValueError("workflow variant case pack identity collision")
        return existing

    def claim_workflow_variant_eval_run(
        self,
        claim: WorkflowVariantEvalRunClaim,
    ) -> bool:
        """Atomically reserve a run id; exact retries are no-op, drift is rejected."""

        self._ensure_writable()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO workflow_eval_run_claims (
                    run_id,
                    input_fingerprint,
                    baseline_version_ref,
                    baseline_definition_hash,
                    candidate_version_ref,
                    candidate_definition_hash,
                    case_pack_id,
                    case_pack_version,
                    case_pack_fingerprint,
                    control_fingerprint,
                    claimed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._claim_values(claim),
            )
            row = connection.execute(
                """
                SELECT *
                FROM workflow_eval_run_claims
                WHERE run_id = ?
                """,
                (claim.run_id,),
            ).fetchone()
            connection.commit()
        if cursor.rowcount == 1:
            return True
        existing = self._claim_from_row(row)
        if existing != claim:
            raise ValueError("workflow variant evaluation run id collision")
        return False

    def fetch_workflow_variant_eval_run_claim(
        self,
        run_id: str,
    ) -> WorkflowVariantEvalRunClaim | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM workflow_eval_run_claims
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._claim_from_row(row)

    def record_workflow_variant_eval_run(
        self,
        run: WorkflowVariantEvalRunContract,
    ) -> WorkflowVariantEvalRunContract:
        """Append one verified evaluation result bound to an existing claim."""

        self._ensure_writable()
        payload = canonical_workflow_variant_eval_payload(run)
        payload_sha256 = workflow_variant_eval_fingerprint(run)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO workflow_eval_runs (
                    run_id,
                    case_pack_id,
                    case_pack_version,
                    case_pack_fingerprint,
                    workflow_profile,
                    route,
                    baseline_version_ref,
                    candidate_version_ref,
                    generated_at,
                    payload,
                    payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.case_pack_id,
                    run.case_pack_version,
                    run.case_pack_fingerprint,
                    run.workflow_profile,
                    run.route,
                    run.baseline_version_ref,
                    run.candidate_version_ref,
                    str(run.generated_at),
                    payload,
                    payload_sha256,
                ),
            )
            row = connection.execute(
                """
                SELECT *
                FROM workflow_eval_runs
                WHERE run_id = ?
                """,
                (run.run_id,),
            ).fetchone()
            connection.commit()
        if cursor.rowcount == 1:
            return run
        existing = self._verified_run_from_row(row)
        if existing is None:
            raise ValueError("stored workflow variant evaluation failed integrity verification")
        if (
            str(row["payload"]) != payload
            or str(row["payload_sha256"]) != payload_sha256
        ):
            raise ValueError("workflow variant evaluation run id collision")
        return existing

    def fetch_workflow_variant_case_pack(
        self,
        *,
        case_pack_id: str,
        case_pack_version: str,
    ) -> WorkflowVariantEvalCasePackContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM workflow_eval_case_packs
                WHERE case_pack_id = ? AND case_pack_version = ?
                """,
                (case_pack_id, case_pack_version),
            ).fetchone()
        return self._verified_case_pack_from_row(row)

    def fetch_workflow_variant_eval_run(
        self,
        run_id: str,
    ) -> WorkflowVariantEvalRunContract | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM workflow_eval_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._verified_run_from_row(row)

    def list_workflow_variant_eval_runs(
        self,
        *,
        workflow_profile: str | None = None,
        route: str | None = None,
        baseline_version_ref: str | None = None,
        candidate_version_ref: str | None = None,
        case_pack_id: str | None = None,
        case_pack_version: str | None = None,
        generated_from: str | None = None,
        generated_to: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WorkflowVariantEvalRunContract]:
        """List verified runs; invalid rows never consume the requested page."""

        clauses: list[str] = []
        params: list[object] = []
        for column, value in (
            ("workflow_profile", workflow_profile),
            ("route", route),
            ("baseline_version_ref", baseline_version_ref),
            ("candidate_version_ref", candidate_version_ref),
            ("case_pack_id", case_pack_id),
            ("case_pack_version", case_pack_version),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        if generated_from is not None:
            clauses.append("generated_at >= ?")
            params.append(generated_from)
        if generated_to is not None:
            clauses.append("generated_at <= ?")
            params.append(generated_to)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM workflow_eval_runs
                {where}
                ORDER BY generated_at DESC, run_id DESC
                """,
                params,
            ).fetchall()
        verified = [
            run
            for row in rows
            if (run := self._verified_run_from_row(row)) is not None
        ]
        return verified[offset : offset + limit]

    def register_technology_radar_intake(
        self,
        intake: TechnologyRadarIntakeContract,
    ) -> TechnologyRadarIntakeContract:
        """Append one reviewed external reference, accepting only an exact retry."""

        self._ensure_writable()
        require_valid_technology_radar_intake(intake)
        payload = canonical_technology_radar_intake_payload(intake)
        payload_sha256 = technology_radar_intake_fingerprint(intake)
        source_locator, source_version_ref = technology_radar_source_identity(
            intake.source_locator,
            intake.source_version_ref,
        )
        self._verify_technology_radar_intake_lineage(intake)
        values = (
            intake.intake_id,
            intake.candidate_ref,
            intake.intake_version,
            intake.technology_name,
            intake.source_kind,
            source_locator,
            source_version_ref,
            intake.source_content_sha256,
            intake.absorption_class,
            self._normalized_technology_radar_timestamp(intake.recorded_at),
            intake.previous_intake_id,
            intake.previous_intake_fingerprint,
            payload,
            payload_sha256,
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO technology_radar_intakes (
                    intake_id,
                    candidate_ref,
                    intake_version,
                    technology_name,
                    source_kind,
                    source_locator,
                    source_version_ref,
                    source_content_sha256,
                    absorption_class,
                    recorded_at,
                    previous_intake_id,
                    previous_intake_fingerprint,
                    payload,
                    payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            if cursor.rowcount == 1:
                return intake
            rows = connection.execute(
                """
                SELECT *
                FROM technology_radar_intakes
                WHERE intake_id = ?
                   OR (candidate_ref = ? AND intake_version = ?)
                   OR (source_locator = ? AND source_version_ref = ?)
                """,
                (
                    intake.intake_id,
                    intake.candidate_ref,
                    intake.intake_version,
                    source_locator,
                    source_version_ref,
                ),
            ).fetchall()
        if len(rows) != 1:
            raise ValueError("technology radar intake identity collision")
        row = rows[0]
        existing = self._verified_technology_radar_intake_from_row(row)
        if existing is None:
            raise ValueError(
                "stored technology radar intake failed integrity verification"
            )
        if self._technology_radar_intake_row_values(row) != values:
            raise ValueError("technology radar intake identity collision")
        return existing

    def _verify_technology_radar_intake_lineage(
        self,
        intake: TechnologyRadarIntakeContract,
    ) -> None:
        previous_id = intake.previous_intake_id
        previous_fingerprint = intake.previous_intake_fingerprint
        if previous_id is None:
            with self._connect() as connection:
                prior = connection.execute(
                    """
                    SELECT 1
                    FROM technology_radar_intakes
                    WHERE candidate_ref = ?
                    LIMIT 1
                    """,
                    (intake.candidate_ref,),
                ).fetchone()
            if prior is not None:
                existing = self.fetch_technology_radar_intake(
                    intake_id=intake.intake_id
                )
                if (
                    existing is not None
                    and technology_radar_intake_fingerprint(existing)
                    == technology_radar_intake_fingerprint(intake)
                ):
                    return
                if existing is not None:
                    raise ValueError(
                        "technology radar intake identity collision"
                    )
                existing = self.fetch_technology_radar_intake(
                    candidate_ref=intake.candidate_ref,
                    intake_version=intake.intake_version,
                )
                if existing is not None:
                    raise ValueError(
                        "technology radar intake identity collision"
                    )
                raise ValueError(
                    "technology radar intake revision requires predecessor lineage"
                )
            return
        previous = self.fetch_technology_radar_intake(intake_id=previous_id)
        if (
            previous is None
            or previous_fingerprint
            != technology_radar_intake_fingerprint(previous)
            or previous.candidate_ref != intake.candidate_ref
        ):
            raise ValueError("technology radar intake predecessor mismatch")
        previous_version = parse_canonical_semver(previous.intake_version)
        current_version = parse_canonical_semver(intake.intake_version)
        if (
            previous_version is None
            or current_version is None
            or current_version <= previous_version
        ):
            raise ValueError("technology radar intake version must advance predecessor")

    def fetch_technology_radar_intake(
        self,
        *,
        intake_id: str | None = None,
        candidate_ref: str | None = None,
        intake_version: str | None = None,
    ) -> TechnologyRadarIntakeContract | None:
        """Resolve one unambiguous intake and fail closed on identity drift or tamper."""

        if not self._technology_radar_store_available():
            return None
        clauses: list[str] = []
        params: list[str] = []
        for column, value in (
            ("intake_id", intake_id),
            ("candidate_ref", candidate_ref),
            ("intake_version", intake_version),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        if not clauses:
            return None
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM technology_radar_intakes
                WHERE {' AND '.join(clauses)}
                ORDER BY recorded_at DESC, intake_id DESC
                LIMIT 2
                """,
                params,
            ).fetchall()
        if len(rows) != 1:
            return None
        return self._verified_technology_radar_intake_from_row(rows[0])

    def list_technology_radar_intakes(
        self,
        *,
        source_kind: str | None = None,
        absorption_class: str | None = None,
        target_gap_ref: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TechnologyRadarIntakeContract]:
        """List a stable page of verified intakes after all filters are applied."""

        if not self._technology_radar_store_available():
            return []
        clauses: list[str] = []
        params: list[str] = []
        for column, value in (
            ("source_kind", source_kind),
            ("absorption_class", absorption_class),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM technology_radar_intakes
                {where}
                ORDER BY recorded_at DESC, intake_id DESC
                """,
                params,
            ).fetchall()
        verified = [
            intake
            for row in rows
            if (intake := self._verified_technology_radar_intake_from_row(row))
            is not None
            and (
                target_gap_ref is None
                or target_gap_ref in intake.target_gap_refs
            )
        ]
        return verified[offset : offset + limit]

    def register_technology_experiment_pack(
        self,
        pack: TechnologyExperimentPackContract,
    ) -> TechnologyExperimentPackContract:
        """Append one intake-bound inert experiment pack; exact retries are safe."""

        self._ensure_writable()
        intake = self.fetch_technology_radar_intake(
            intake_id=pack.intake_id,
            candidate_ref=pack.candidate_ref,
            intake_version=pack.intake_version,
        )
        if intake is None:
            raise ValueError(
                "technology experiment pack requires a verified radar intake"
            )
        require_valid_technology_experiment_pack(pack, intake=intake)
        payload = canonical_technology_experiment_payload(pack)
        payload_sha256 = technology_experiment_pack_fingerprint(pack)
        values = self._technology_experiment_pack_values(
            pack,
            payload=payload,
            payload_sha256=payload_sha256,
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO technology_experiment_packs (
                    experiment_pack_id,
                    pack_version,
                    intake_id,
                    intake_version,
                    intake_fingerprint,
                    reviewed_payload_fingerprint,
                    candidate_ref,
                    source_content_sha256,
                    absorption_class,
                    translation_kind,
                    pattern_id,
                    sovereign_consumer_ref,
                    target_gap_refs,
                    license_id,
                    license_status,
                    license_evidence_ref,
                    pack_status,
                    generated_at,
                    payload,
                    payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            row = connection.execute(
                """
                SELECT *
                FROM technology_experiment_packs
                WHERE experiment_pack_id = ? AND pack_version = ?
                """,
                (pack.experiment_pack_id, pack.pack_version),
            ).fetchone()
        if cursor.rowcount == 1:
            return pack
        existing = self._verified_technology_experiment_pack_from_row(row)
        if existing is None:
            raise ValueError(
                "stored technology experiment pack failed integrity verification"
            )
        if row is None or self._technology_experiment_pack_row_values(row) != values:
            raise ValueError("technology experiment pack identity collision")
        return existing

    def fetch_technology_experiment_pack(
        self,
        *,
        experiment_pack_id: str,
        pack_version: str,
    ) -> TechnologyExperimentPackContract | None:
        """Resolve one exact pack and revalidate its complete intake binding."""

        if not self._table_available("technology_experiment_packs"):
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM technology_experiment_packs
                WHERE experiment_pack_id = ? AND pack_version = ?
                """,
                (experiment_pack_id, pack_version),
            ).fetchone()
        return self._verified_technology_experiment_pack_from_row(row)

    def list_technology_experiment_packs(
        self,
        *,
        intake_id: str | None = None,
        candidate_ref: str | None = None,
        absorption_class: str | None = None,
        sovereign_consumer_ref: str | None = None,
        pattern_id: str | None = None,
        target_gap_ref: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TechnologyExperimentPackContract]:
        """List verified packs without letting invalid rows consume the page."""

        if not self._table_available("technology_experiment_packs"):
            return []
        clauses: list[str] = []
        params: list[str] = []
        for column, value in (
            ("intake_id", intake_id),
            ("candidate_ref", candidate_ref),
            ("absorption_class", absorption_class),
            ("sovereign_consumer_ref", sovereign_consumer_ref),
            ("pattern_id", pattern_id),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM technology_experiment_packs
                {where}
                ORDER BY generated_at DESC, experiment_pack_id DESC, pack_version DESC
                """,
                params,
            ).fetchall()
        verified = [
            pack
            for row in rows
            if (
                pack := self._verified_technology_experiment_pack_from_row(row)
            )
            is not None
            and (
                target_gap_ref is None
                or target_gap_ref in pack.target_gap_refs
            )
        ]
        return verified[offset : offset + limit]

    def claim_technology_experiment_eval_run(
        self,
        claim: TechnologyExperimentEvalRunClaimContract,
    ) -> bool:
        """Atomically reserve a run id; exact retries are reported as no-ops."""

        self._ensure_writable()
        pack = self.fetch_technology_experiment_pack(
            experiment_pack_id=claim.experiment_pack_id,
            pack_version=claim.pack_version,
        )
        if pack is None:
            raise ValueError(
                "technology experiment run claim requires a verified pack"
            )
        blockers = validate_technology_experiment_eval_run_claim(claim, pack=pack)
        if blockers:
            raise ValueError(
                "technology experiment run claim is invalid: "
                + "; ".join(blockers)
            )
        payload = canonical_technology_experiment_payload(claim)
        payload_sha256 = technology_experiment_artifact_fingerprint(claim)
        values = self._technology_experiment_claim_values(
            claim,
            payload=payload,
            payload_sha256=payload_sha256,
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO technology_experiment_eval_run_claims (
                    run_id,
                    experiment_pack_id,
                    pack_version,
                    pack_fingerprint,
                    intake_id,
                    intake_fingerprint,
                    input_fingerprint,
                    control_fingerprint,
                    claimed_at,
                    payload,
                    payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            row = connection.execute(
                """
                SELECT *
                FROM technology_experiment_eval_run_claims
                WHERE run_id = ?
                """,
                (claim.run_id,),
            ).fetchone()
        if cursor.rowcount == 1:
            return True
        existing = self._verified_technology_experiment_claim_from_row(row)
        if (
            existing is None
            or existing != claim
            or row is None
            or self._technology_experiment_claim_row_values(row) != values
        ):
            raise ValueError("technology experiment evaluation run id collision")
        return False

    def fetch_technology_experiment_eval_run_claim(
        self,
        run_id: str,
    ) -> TechnologyExperimentEvalRunClaimContract | None:
        if not self._table_available("technology_experiment_eval_run_claims"):
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM technology_experiment_eval_run_claims
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._verified_technology_experiment_claim_from_row(row)

    def record_technology_experiment_eval_run(
        self,
        run: TechnologyExperimentEvalRunContract,
    ) -> TechnologyExperimentEvalRunContract:
        """Append one derived result bound to an exact verified pack and claim."""

        self._ensure_writable()
        pack = self.fetch_technology_experiment_pack(
            experiment_pack_id=run.experiment_pack_id,
            pack_version=run.pack_version,
        )
        if pack is None:
            raise ValueError("technology experiment eval run requires a verified pack")
        intake = self.fetch_technology_radar_intake(
            intake_id=pack.intake_id,
            candidate_ref=pack.candidate_ref,
            intake_version=pack.intake_version,
        )
        if intake is None:
            raise ValueError("technology experiment eval run requires a verified intake")
        require_valid_technology_experiment_eval_run(
            run,
            pack=pack,
            intake=intake,
        )
        claim = self.fetch_technology_experiment_eval_run_claim(run.run_id)
        if claim is None:
            raise ValueError("technology experiment eval run requires an existing claim")
        if (
            claim.experiment_pack_id != run.experiment_pack_id
            or claim.pack_version != run.pack_version
            or claim.pack_fingerprint != run.pack_fingerprint
            or claim.intake_id != run.intake_id
            or claim.intake_fingerprint != run.intake_fingerprint
            or claim.input_fingerprint != run.input_fingerprint
            or claim.control_fingerprint != run.control_fingerprint
        ):
            raise ValueError(
                "technology experiment eval run does not match its immutable claim"
            )
        if self._technology_experiment_timestamp(
            str(claim.claimed_at)
        ) > self._technology_experiment_timestamp(str(run.generated_at)):
            raise ValueError(
                "technology experiment eval run cannot predate its immutable claim"
            )
        payload = canonical_technology_experiment_payload(run)
        payload_sha256 = technology_experiment_eval_run_fingerprint(run)
        values = self._technology_experiment_run_values(
            run,
            payload=payload,
            payload_sha256=payload_sha256,
        )
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO technology_experiment_eval_runs (
                    run_id,
                    experiment_pack_id,
                    pack_version,
                    pack_fingerprint,
                    intake_id,
                    intake_version,
                    intake_fingerprint,
                    candidate_ref,
                    pattern_id,
                    sovereign_consumer_ref,
                    input_fingerprint,
                    control_fingerprint,
                    status,
                    readiness_status,
                    promotion_readiness,
                    total_cases,
                    passed_cases,
                    failed_cases,
                    pass_rate,
                    generated_at,
                    payload,
                    payload_sha256
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            row = connection.execute(
                """
                SELECT *
                FROM technology_experiment_eval_runs
                WHERE run_id = ?
                """,
                (run.run_id,),
            ).fetchone()
        if cursor.rowcount == 1:
            return run
        existing = self._verified_technology_experiment_run_from_row(row)
        if existing is None:
            raise ValueError(
                "stored technology experiment eval run failed integrity verification"
            )
        if row is None or self._technology_experiment_run_row_values(row) != values:
            raise ValueError("technology experiment evaluation run id collision")
        return existing

    def fetch_technology_experiment_eval_run(
        self,
        run_id: str,
    ) -> TechnologyExperimentEvalRunContract | None:
        if not self._table_available("technology_experiment_eval_runs"):
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM technology_experiment_eval_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._verified_technology_experiment_run_from_row(row)

    def list_technology_experiment_eval_runs(
        self,
        *,
        experiment_pack_id: str | None = None,
        pack_version: str | None = None,
        intake_id: str | None = None,
        candidate_ref: str | None = None,
        pattern_id: str | None = None,
        sovereign_consumer_ref: str | None = None,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[TechnologyExperimentEvalRunContract]:
        """List verified derived runs after filtering and before paging."""

        if not self._table_available("technology_experiment_eval_runs"):
            return []
        clauses: list[str] = []
        params: list[str] = []
        for column, value in (
            ("experiment_pack_id", experiment_pack_id),
            ("pack_version", pack_version),
            ("intake_id", intake_id),
            ("candidate_ref", candidate_ref),
            ("pattern_id", pattern_id),
            ("sovereign_consumer_ref", sovereign_consumer_ref),
            ("status", status),
        ):
            if value is not None:
                clauses.append(f"{column} = ?")
                params.append(value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM technology_experiment_eval_runs
                {where}
                ORDER BY generated_at DESC, run_id DESC
                """,
                params,
            ).fetchall()
        verified = [
            run
            for row in rows
            if (run := self._verified_technology_experiment_run_from_row(row))
            is not None
        ]
        return verified[offset : offset + limit]

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
                    optimization_scope TEXT,
                    optimization_target_kind TEXT,
                    optimization_candidate_status TEXT,
                    optimization_safety_status TEXT,
                    optimization_blockers TEXT NOT NULL DEFAULT '[]',
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
                    optimization_scope TEXT,
                    optimization_target_kind TEXT,
                    optimization_readiness TEXT,
                    optimization_release_status TEXT,
                    optimization_safety_status TEXT,
                    optimization_blockers TEXT NOT NULL DEFAULT '[]',
                    baseline_label TEXT,
                    candidate_label TEXT,
                    selected_candidate_label TEXT,
                    selection_criteria TEXT NOT NULL DEFAULT '{}',
                    baseline_metrics TEXT NOT NULL DEFAULT '{}',
                    candidate_metrics TEXT NOT NULL DEFAULT '{}',
                    metric_deltas TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS workflow_eval_case_packs (
                    case_pack_id TEXT NOT NULL,
                    case_pack_version TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    route TEXT NOT NULL,
                    baseline_version_ref TEXT NOT NULL,
                    candidate_version_ref TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    PRIMARY KEY (case_pack_id, case_pack_version)
                );

                CREATE TABLE IF NOT EXISTS workflow_eval_run_claims (
                    run_id TEXT PRIMARY KEY,
                    input_fingerprint TEXT NOT NULL,
                    baseline_version_ref TEXT NOT NULL,
                    baseline_definition_hash TEXT NOT NULL,
                    candidate_version_ref TEXT NOT NULL,
                    candidate_definition_hash TEXT NOT NULL,
                    case_pack_id TEXT NOT NULL,
                    case_pack_version TEXT NOT NULL,
                    case_pack_fingerprint TEXT NOT NULL,
                    control_fingerprint TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    FOREIGN KEY (case_pack_id, case_pack_version)
                        REFERENCES workflow_eval_case_packs (
                            case_pack_id, case_pack_version
                        )
                );

                CREATE TABLE IF NOT EXISTS workflow_eval_runs (
                    run_id TEXT PRIMARY KEY,
                    case_pack_id TEXT NOT NULL,
                    case_pack_version TEXT NOT NULL,
                    case_pack_fingerprint TEXT NOT NULL,
                    workflow_profile TEXT NOT NULL,
                    route TEXT NOT NULL,
                    baseline_version_ref TEXT NOT NULL,
                    candidate_version_ref TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (run_id)
                        REFERENCES workflow_eval_run_claims (run_id),
                    FOREIGN KEY (case_pack_id, case_pack_version)
                        REFERENCES workflow_eval_case_packs (
                            case_pack_id, case_pack_version
                        )
                );

                CREATE INDEX IF NOT EXISTS workflow_eval_runs_scope_time_idx
                    ON workflow_eval_runs (
                        workflow_profile,
                        route,
                        baseline_version_ref,
                        candidate_version_ref,
                        generated_at DESC
                    );
                CREATE INDEX IF NOT EXISTS workflow_eval_runs_pack_time_idx
                    ON workflow_eval_runs (
                        case_pack_id,
                        case_pack_version,
                        generated_at DESC
                    );
                CREATE INDEX IF NOT EXISTS workflow_eval_runs_generated_at_idx
                    ON workflow_eval_runs (generated_at DESC);

                CREATE TABLE IF NOT EXISTS workflow_lifecycle_release_bundles (
                    transition_id TEXT PRIMARY KEY,
                    workflow_profile TEXT NOT NULL,
                    route TEXT NOT NULL,
                    revision INTEGER NOT NULL CHECK (revision > 0),
                    transition_action TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    UNIQUE (workflow_profile, route, revision)
                );

                CREATE INDEX IF NOT EXISTS workflow_lifecycle_release_scope_idx
                    ON workflow_lifecycle_release_bundles (
                        workflow_profile,
                        route,
                        revision DESC
                    );

                CREATE TABLE IF NOT EXISTS technology_radar_intakes (
                    intake_id TEXT PRIMARY KEY,
                    candidate_ref TEXT NOT NULL,
                    intake_version TEXT NOT NULL,
                    technology_name TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    source_locator TEXT NOT NULL,
                    source_version_ref TEXT NOT NULL,
                    source_content_sha256 TEXT NOT NULL,
                    absorption_class TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    previous_intake_id TEXT,
                    previous_intake_fingerprint TEXT,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    UNIQUE (candidate_ref, intake_version),
                    UNIQUE (source_locator, source_version_ref),
                    UNIQUE (previous_intake_id),
                    FOREIGN KEY (previous_intake_id)
                        REFERENCES technology_radar_intakes (intake_id)
                );

                CREATE INDEX IF NOT EXISTS technology_radar_intakes_scope_time_idx
                    ON technology_radar_intakes (
                        source_kind,
                        absorption_class,
                        recorded_at DESC,
                        intake_id DESC
                    );

                CREATE UNIQUE INDEX IF NOT EXISTS technology_radar_intakes_genesis_idx
                    ON technology_radar_intakes (candidate_ref)
                    WHERE previous_intake_id IS NULL;

                CREATE TABLE IF NOT EXISTS technology_experiment_packs (
                    experiment_pack_id TEXT NOT NULL,
                    pack_version TEXT NOT NULL,
                    intake_id TEXT NOT NULL,
                    intake_version TEXT NOT NULL,
                    intake_fingerprint TEXT NOT NULL,
                    reviewed_payload_fingerprint TEXT NOT NULL,
                    candidate_ref TEXT NOT NULL,
                    source_content_sha256 TEXT NOT NULL,
                    absorption_class TEXT NOT NULL,
                    translation_kind TEXT NOT NULL,
                    pattern_id TEXT NOT NULL,
                    sovereign_consumer_ref TEXT NOT NULL,
                    target_gap_refs TEXT NOT NULL,
                    license_id TEXT NOT NULL,
                    license_status TEXT NOT NULL,
                    license_evidence_ref TEXT NOT NULL,
                    pack_status TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    PRIMARY KEY (experiment_pack_id, pack_version),
                    FOREIGN KEY (intake_id)
                        REFERENCES technology_radar_intakes (intake_id)
                );

                CREATE TABLE IF NOT EXISTS technology_experiment_eval_run_claims (
                    run_id TEXT PRIMARY KEY,
                    experiment_pack_id TEXT NOT NULL,
                    pack_version TEXT NOT NULL,
                    pack_fingerprint TEXT NOT NULL,
                    intake_id TEXT NOT NULL,
                    intake_fingerprint TEXT NOT NULL,
                    input_fingerprint TEXT NOT NULL,
                    control_fingerprint TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (experiment_pack_id, pack_version)
                        REFERENCES technology_experiment_packs (
                            experiment_pack_id, pack_version
                        )
                );

                CREATE TABLE IF NOT EXISTS technology_experiment_eval_runs (
                    run_id TEXT PRIMARY KEY,
                    experiment_pack_id TEXT NOT NULL,
                    pack_version TEXT NOT NULL,
                    pack_fingerprint TEXT NOT NULL,
                    intake_id TEXT NOT NULL,
                    intake_version TEXT NOT NULL,
                    intake_fingerprint TEXT NOT NULL,
                    candidate_ref TEXT NOT NULL,
                    pattern_id TEXT NOT NULL,
                    sovereign_consumer_ref TEXT NOT NULL,
                    input_fingerprint TEXT NOT NULL,
                    control_fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    readiness_status TEXT NOT NULL,
                    promotion_readiness TEXT NOT NULL,
                    total_cases INTEGER NOT NULL CHECK (total_cases > 0),
                    passed_cases INTEGER NOT NULL CHECK (passed_cases >= 0),
                    failed_cases INTEGER NOT NULL CHECK (failed_cases >= 0),
                    pass_rate REAL NOT NULL CHECK (pass_rate >= 0 AND pass_rate <= 1),
                    generated_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    FOREIGN KEY (run_id)
                        REFERENCES technology_experiment_eval_run_claims (run_id),
                    FOREIGN KEY (experiment_pack_id, pack_version)
                        REFERENCES technology_experiment_packs (
                            experiment_pack_id, pack_version
                        )
                );

                CREATE INDEX IF NOT EXISTS technology_experiment_packs_scope_time_idx
                    ON technology_experiment_packs (
                        intake_id,
                        candidate_ref,
                        absorption_class,
                        sovereign_consumer_ref,
                        pattern_id,
                        generated_at DESC
                    );

                CREATE INDEX IF NOT EXISTS technology_experiment_eval_runs_scope_time_idx
                    ON technology_experiment_eval_runs (
                        experiment_pack_id,
                        pack_version,
                        intake_id,
                        candidate_ref,
                        pattern_id,
                        status,
                        generated_at DESC
                    );

                CREATE INDEX IF NOT EXISTS technology_experiment_eval_runs_time_idx
                    ON technology_experiment_eval_runs (generated_at DESC, run_id DESC);

                CREATE TRIGGER IF NOT EXISTS technology_radar_intakes_no_update
                BEFORE UPDATE ON technology_radar_intakes
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_radar_intakes is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS technology_radar_intakes_no_delete
                BEFORE DELETE ON technology_radar_intakes
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_radar_intakes is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS technology_experiment_packs_no_update
                BEFORE UPDATE ON technology_experiment_packs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_experiment_packs is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS technology_experiment_packs_no_delete
                BEFORE DELETE ON technology_experiment_packs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_experiment_packs is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS technology_experiment_eval_run_claims_no_update
                BEFORE UPDATE ON technology_experiment_eval_run_claims
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_experiment_eval_run_claims is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS technology_experiment_eval_run_claims_no_delete
                BEFORE DELETE ON technology_experiment_eval_run_claims
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_experiment_eval_run_claims is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS technology_experiment_eval_runs_no_update
                BEFORE UPDATE ON technology_experiment_eval_runs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_experiment_eval_runs is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS technology_experiment_eval_runs_no_delete
                BEFORE DELETE ON technology_experiment_eval_runs
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'technology_experiment_eval_runs is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_eval_case_packs_no_update
                BEFORE UPDATE ON workflow_eval_case_packs
                BEGIN
                    SELECT RAISE(ABORT, 'workflow_eval_case_packs is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_eval_case_packs_no_delete
                BEFORE DELETE ON workflow_eval_case_packs
                BEGIN
                    SELECT RAISE(ABORT, 'workflow_eval_case_packs is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_eval_run_claims_no_update
                BEFORE UPDATE ON workflow_eval_run_claims
                BEGIN
                    SELECT RAISE(ABORT, 'workflow_eval_run_claims is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_eval_run_claims_no_delete
                BEFORE DELETE ON workflow_eval_run_claims
                BEGIN
                    SELECT RAISE(ABORT, 'workflow_eval_run_claims is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_eval_runs_no_update
                BEFORE UPDATE ON workflow_eval_runs
                BEGIN
                    SELECT RAISE(ABORT, 'workflow_eval_runs is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_eval_runs_no_delete
                BEFORE DELETE ON workflow_eval_runs
                BEGIN
                    SELECT RAISE(ABORT, 'workflow_eval_runs is append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_lifecycle_release_bundles_no_update
                BEFORE UPDATE ON workflow_lifecycle_release_bundles
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'workflow_lifecycle_release_bundles is append-only'
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS workflow_lifecycle_release_bundles_no_delete
                BEFORE DELETE ON workflow_lifecycle_release_bundles
                BEGIN
                    SELECT RAISE(
                        ABORT,
                        'workflow_lifecycle_release_bundles is append-only'
                    );
                END;
                """
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "optimization_scope",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "optimization_target_kind",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "optimization_candidate_status",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "optimization_safety_status",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_proposals",
                "optimization_blockers",
                "TEXT NOT NULL DEFAULT '[]'",
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
                "optimization_scope",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "optimization_target_kind",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "optimization_readiness",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "optimization_release_status",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "optimization_safety_status",
                "TEXT",
            )
            self._ensure_column(
                connection,
                "evolution_decisions",
                "optimization_blockers",
                "TEXT NOT NULL DEFAULT '[]'",
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
        if self.read_only:
            if not self.database_path.is_file():
                raise FileNotFoundError(self.database_path)
            database_uri = f"{self.database_path.resolve().as_uri()}?mode=ro"
            connection = connect(
                database_uri,
                timeout=30.0,
                uri=True,
            )
            connection.execute("PRAGMA query_only = ON")
        else:
            connection = connect(self.database_path, timeout=30.0)
        connection.row_factory = Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def _technology_radar_store_available(self) -> bool:
        return self._table_available("technology_radar_intakes")

    def _table_available(self, table_name: str) -> bool:
        if not self.database_path.is_file():
            return False
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM sqlite_schema
                WHERE type = 'table'
                  AND name = ?
                LIMIT 1
                """,
                (table_name,),
            ).fetchone()
        return row is not None

    def _ensure_writable(self) -> None:
        if self.read_only:
            raise PermissionError("evolution lab repository is read-only")

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
            optimization_scope=row["optimization_scope"],
            optimization_target_kind=row["optimization_target_kind"],
            optimization_candidate_status=row["optimization_candidate_status"],
            optimization_safety_status=row["optimization_safety_status"],
            optimization_blockers=loads(row["optimization_blockers"] or "[]"),
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
            optimization_scope=row["optimization_scope"],
            optimization_target_kind=row["optimization_target_kind"],
            optimization_readiness=row["optimization_readiness"],
            optimization_release_status=row["optimization_release_status"],
            optimization_safety_status=row["optimization_safety_status"],
            optimization_blockers=loads(row["optimization_blockers"] or "[]"),
            baseline_label=row["baseline_label"],
            candidate_label=row["candidate_label"],
            selected_candidate_label=row["selected_candidate_label"],
            selection_criteria=loads(row["selection_criteria"] or "{}"),
            baseline_metrics=loads(row["baseline_metrics"] or "{}"),
            candidate_metrics=loads(row["candidate_metrics"] or "{}"),
            metric_deltas=loads(row["metric_deltas"] or "{}"),
        )

    @staticmethod
    def _technology_radar_intake_row_values(
        row: Row,
    ) -> tuple[object, ...]:
        return (
            str(row["intake_id"]),
            str(row["candidate_ref"]),
            str(row["intake_version"]),
            str(row["technology_name"]),
            str(row["source_kind"]),
            str(row["source_locator"]),
            str(row["source_version_ref"]),
            str(row["source_content_sha256"]),
            str(row["absorption_class"]),
            str(row["recorded_at"]),
            (
                str(row["previous_intake_id"])
                if row["previous_intake_id"] is not None
                else None
            ),
            (
                str(row["previous_intake_fingerprint"])
                if row["previous_intake_fingerprint"] is not None
                else None
            ),
            str(row["payload"]),
            str(row["payload_sha256"]),
        )

    @staticmethod
    def _normalized_technology_radar_timestamp(value: str) -> str:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            UTC
        ).isoformat()

    def _verified_technology_radar_intake_from_row(
        self,
        row: Row | None,
    ) -> TechnologyRadarIntakeContract | None:
        intake = self._locally_verified_technology_radar_intake_from_row(row)
        if intake is None:
            return None
        terminal = intake
        seen = {intake.intake_id}
        while intake.previous_intake_id is not None:
            if intake.previous_intake_id in seen:
                return None
            seen.add(intake.previous_intake_id)
            with self._connect() as connection:
                previous_row = connection.execute(
                    """
                    SELECT *
                    FROM technology_radar_intakes
                    WHERE intake_id = ?
                    """,
                    (intake.previous_intake_id,),
                ).fetchone()
            previous = self._locally_verified_technology_radar_intake_from_row(
                previous_row
            )
            previous_version = (
                parse_canonical_semver(previous.intake_version)
                if previous is not None
                else None
            )
            current_version = parse_canonical_semver(intake.intake_version)
            if (
                previous is None
                or intake.previous_intake_fingerprint
                != technology_radar_intake_fingerprint(previous)
                or previous.candidate_ref != intake.candidate_ref
                or previous_version is None
                or current_version is None
                or current_version <= previous_version
            ):
                return None
            intake = previous
        return terminal

    @classmethod
    def _locally_verified_technology_radar_intake_from_row(
        cls,
        row: Row | None,
    ) -> TechnologyRadarIntakeContract | None:
        if row is None:
            return None
        payload = str(row["payload"])
        payload_sha256 = str(row["payload_sha256"])
        if sha256(payload.encode("utf-8")).hexdigest() != payload_sha256:
            return None
        try:
            decoded = loads(payload)
            if not isinstance(decoded, dict):
                return None
            intake = TechnologyRadarIntakeContract(**decoded)
            require_valid_technology_radar_intake(intake)
        except (KeyError, TypeError, ValueError):
            return None
        if (
            canonical_technology_radar_intake_payload(intake) != payload
            or technology_radar_intake_fingerprint(intake) != payload_sha256
            or intake.intake_id != str(row["intake_id"])
            or intake.candidate_ref != str(row["candidate_ref"])
            or intake.intake_version != str(row["intake_version"])
            or intake.technology_name != str(row["technology_name"])
            or intake.source_kind != str(row["source_kind"])
            or intake.source_locator != str(row["source_locator"])
            or intake.source_version_ref != str(row["source_version_ref"])
            or intake.source_content_sha256
            != str(row["source_content_sha256"])
            or intake.absorption_class != str(row["absorption_class"])
            or cls._normalized_technology_radar_timestamp(intake.recorded_at)
            != str(row["recorded_at"])
            or intake.previous_intake_id != row["previous_intake_id"]
            or intake.previous_intake_fingerprint
            != row["previous_intake_fingerprint"]
        ):
            return None
        return intake

    @staticmethod
    def _technology_experiment_pack_values(
        pack: TechnologyExperimentPackContract,
        *,
        payload: str,
        payload_sha256: str,
    ) -> tuple[object, ...]:
        return (
            pack.experiment_pack_id,
            pack.pack_version,
            pack.intake_id,
            pack.intake_version,
            pack.intake_fingerprint,
            pack.reviewed_payload_fingerprint,
            pack.candidate_ref,
            pack.source_content_sha256,
            pack.absorption_class,
            pack.translation_kind,
            pack.pattern_id,
            pack.sovereign_consumer_ref,
            canonical_technology_experiment_payload(pack.target_gap_refs),
            pack.license_id,
            pack.license_status,
            pack.license_evidence_ref,
            pack.pack_status,
            str(pack.generated_at),
            payload,
            payload_sha256,
        )

    @staticmethod
    def _technology_experiment_pack_row_values(
        row: Row,
    ) -> tuple[object, ...]:
        return (
            str(row["experiment_pack_id"]),
            str(row["pack_version"]),
            str(row["intake_id"]),
            str(row["intake_version"]),
            str(row["intake_fingerprint"]),
            str(row["reviewed_payload_fingerprint"]),
            str(row["candidate_ref"]),
            str(row["source_content_sha256"]),
            str(row["absorption_class"]),
            str(row["translation_kind"]),
            str(row["pattern_id"]),
            str(row["sovereign_consumer_ref"]),
            str(row["target_gap_refs"]),
            str(row["license_id"]),
            str(row["license_status"]),
            str(row["license_evidence_ref"]),
            str(row["pack_status"]),
            str(row["generated_at"]),
            str(row["payload"]),
            str(row["payload_sha256"]),
        )

    @staticmethod
    def _technology_experiment_claim_values(
        claim: TechnologyExperimentEvalRunClaimContract,
        *,
        payload: str,
        payload_sha256: str,
    ) -> tuple[str, ...]:
        return (
            claim.run_id,
            claim.experiment_pack_id,
            claim.pack_version,
            claim.pack_fingerprint,
            claim.intake_id,
            claim.intake_fingerprint,
            claim.input_fingerprint,
            claim.control_fingerprint,
            str(claim.claimed_at),
            payload,
            payload_sha256,
        )

    @staticmethod
    def _technology_experiment_claim_row_values(
        row: Row,
    ) -> tuple[str, ...]:
        return (
            str(row["run_id"]),
            str(row["experiment_pack_id"]),
            str(row["pack_version"]),
            str(row["pack_fingerprint"]),
            str(row["intake_id"]),
            str(row["intake_fingerprint"]),
            str(row["input_fingerprint"]),
            str(row["control_fingerprint"]),
            str(row["claimed_at"]),
            str(row["payload"]),
            str(row["payload_sha256"]),
        )

    @staticmethod
    def _technology_experiment_run_values(
        run: TechnologyExperimentEvalRunContract,
        *,
        payload: str,
        payload_sha256: str,
    ) -> tuple[object, ...]:
        return (
            run.run_id,
            run.experiment_pack_id,
            run.pack_version,
            run.pack_fingerprint,
            run.intake_id,
            run.intake_version,
            run.intake_fingerprint,
            run.candidate_ref,
            run.pattern_id,
            run.sovereign_consumer_ref,
            run.input_fingerprint,
            run.control_fingerprint,
            run.status,
            run.readiness_status,
            run.promotion_readiness,
            run.total_cases,
            run.passed_cases,
            run.failed_cases,
            run.pass_rate,
            str(run.generated_at),
            payload,
            payload_sha256,
        )

    @staticmethod
    def _technology_experiment_run_row_values(
        row: Row,
    ) -> tuple[object, ...]:
        return (
            str(row["run_id"]),
            str(row["experiment_pack_id"]),
            str(row["pack_version"]),
            str(row["pack_fingerprint"]),
            str(row["intake_id"]),
            str(row["intake_version"]),
            str(row["intake_fingerprint"]),
            str(row["candidate_ref"]),
            str(row["pattern_id"]),
            str(row["sovereign_consumer_ref"]),
            str(row["input_fingerprint"]),
            str(row["control_fingerprint"]),
            str(row["status"]),
            str(row["readiness_status"]),
            str(row["promotion_readiness"]),
            int(row["total_cases"]),
            int(row["passed_cases"]),
            int(row["failed_cases"]),
            float(row["pass_rate"]),
            str(row["generated_at"]),
            str(row["payload"]),
            str(row["payload_sha256"]),
        )

    @staticmethod
    def _technology_experiment_timestamp(value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)

    def _verified_technology_experiment_pack_from_row(
        self,
        row: Row | None,
    ) -> TechnologyExperimentPackContract | None:
        if row is None:
            return None
        payload = str(row["payload"])
        payload_sha256 = str(row["payload_sha256"])
        if sha256(payload.encode("utf-8")).hexdigest() != payload_sha256:
            return None
        try:
            pack = self._technology_experiment_pack_from_payload(payload)
            intake = self.fetch_technology_radar_intake(
                intake_id=pack.intake_id,
                candidate_ref=pack.candidate_ref,
                intake_version=pack.intake_version,
            )
            if intake is None:
                return None
            require_valid_technology_experiment_pack(pack, intake=intake)
        except (KeyError, TypeError, ValueError):
            return None
        if (
            canonical_technology_experiment_payload(pack) != payload
            or technology_experiment_pack_fingerprint(pack) != payload_sha256
            or self._technology_experiment_pack_row_values(row)
            != self._technology_experiment_pack_values(
                pack,
                payload=payload,
                payload_sha256=payload_sha256,
            )
        ):
            return None
        return pack

    def _verified_technology_experiment_claim_from_row(
        self,
        row: Row | None,
    ) -> TechnologyExperimentEvalRunClaimContract | None:
        if row is None:
            return None
        payload = str(row["payload"])
        payload_sha256 = str(row["payload_sha256"])
        if sha256(payload.encode("utf-8")).hexdigest() != payload_sha256:
            return None
        try:
            decoded = loads(payload)
            if not isinstance(decoded, dict):
                return None
            claim = TechnologyExperimentEvalRunClaimContract(**decoded)
            pack = self.fetch_technology_experiment_pack(
                experiment_pack_id=claim.experiment_pack_id,
                pack_version=claim.pack_version,
            )
            if pack is None or validate_technology_experiment_eval_run_claim(
                claim,
                pack=pack,
            ):
                return None
        except (KeyError, TypeError, ValueError):
            return None
        if (
            canonical_technology_experiment_payload(claim) != payload
            or technology_experiment_artifact_fingerprint(claim) != payload_sha256
            or self._technology_experiment_claim_row_values(row)
            != self._technology_experiment_claim_values(
                claim,
                payload=payload,
                payload_sha256=payload_sha256,
            )
        ):
            return None
        return claim

    def _verified_technology_experiment_run_from_row(
        self,
        row: Row | None,
    ) -> TechnologyExperimentEvalRunContract | None:
        if row is None:
            return None
        payload = str(row["payload"])
        payload_sha256 = str(row["payload_sha256"])
        if sha256(payload.encode("utf-8")).hexdigest() != payload_sha256:
            return None
        try:
            run = self._technology_experiment_run_from_payload(payload)
            pack = self.fetch_technology_experiment_pack(
                experiment_pack_id=run.experiment_pack_id,
                pack_version=run.pack_version,
            )
            if pack is None:
                return None
            intake = self.fetch_technology_radar_intake(
                intake_id=pack.intake_id,
                candidate_ref=pack.candidate_ref,
                intake_version=pack.intake_version,
            )
            if intake is None:
                return None
            require_valid_technology_experiment_eval_run(
                run,
                pack=pack,
                intake=intake,
            )
            claim = self.fetch_technology_experiment_eval_run_claim(run.run_id)
        except (KeyError, TypeError, ValueError):
            return None
        if (
            claim is None
            or claim.experiment_pack_id != run.experiment_pack_id
            or claim.pack_version != run.pack_version
            or claim.pack_fingerprint != run.pack_fingerprint
            or claim.intake_id != run.intake_id
            or claim.intake_fingerprint != run.intake_fingerprint
            or claim.input_fingerprint != run.input_fingerprint
            or claim.control_fingerprint != run.control_fingerprint
            or self._technology_experiment_timestamp(str(claim.claimed_at))
            > self._technology_experiment_timestamp(str(run.generated_at))
            or canonical_technology_experiment_payload(run) != payload
            or technology_experiment_eval_run_fingerprint(run) != payload_sha256
            or self._technology_experiment_run_row_values(row)
            != self._technology_experiment_run_values(
                run,
                payload=payload,
                payload_sha256=payload_sha256,
            )
        ):
            return None
        return run

    @classmethod
    def _technology_experiment_pack_from_payload(
        cls,
        payload: str,
    ) -> TechnologyExperimentPackContract:
        value = loads(payload)
        return TechnologyExperimentPackContract(
            **{
                **value,
                "cases": [
                    cls._technology_experiment_case_from_dict(case)
                    for case in value["cases"]
                ],
            }
        )

    @staticmethod
    def _technology_experiment_control_from_dict(
        value: dict[str, object],
    ) -> TechnologyExperimentControlSnapshotContract:
        return TechnologyExperimentControlSnapshotContract(**value)

    @staticmethod
    def _technology_experiment_observation_from_dict(
        value: dict[str, object],
    ) -> TechnologyExperimentObservationContract:
        return TechnologyExperimentObservationContract(**value)

    @classmethod
    def _technology_experiment_case_from_dict(
        cls,
        value: dict[str, object],
    ) -> TechnologyExperimentCaseContract:
        return TechnologyExperimentCaseContract(
            **{
                **value,
                "control_snapshot": cls._technology_experiment_control_from_dict(
                    value["control_snapshot"]
                ),
                "baseline_observation": (
                    cls._technology_experiment_observation_from_dict(
                        value["baseline_observation"]
                    )
                ),
                "candidate_observation": (
                    cls._technology_experiment_observation_from_dict(
                        value["candidate_observation"]
                    )
                ),
            }
        )

    @staticmethod
    def _technology_experiment_case_result_from_dict(
        value: dict[str, object],
    ) -> TechnologyExperimentCaseResultContract:
        return TechnologyExperimentCaseResultContract(**value)

    @classmethod
    def _technology_experiment_run_from_payload(
        cls,
        payload: str,
    ) -> TechnologyExperimentEvalRunContract:
        value = loads(payload)
        return TechnologyExperimentEvalRunContract(
            **{
                **value,
                "case_results": [
                    cls._technology_experiment_case_result_from_dict(result)
                    for result in value["case_results"]
                ],
            }
        )

    @staticmethod
    def _claim_values(claim: WorkflowVariantEvalRunClaim) -> tuple[str, ...]:
        return (
            claim.run_id,
            claim.input_fingerprint,
            claim.baseline_version_ref,
            claim.baseline_definition_hash,
            claim.candidate_version_ref,
            claim.candidate_definition_hash,
            claim.case_pack_id,
            claim.case_pack_version,
            claim.case_pack_fingerprint,
            claim.control_fingerprint,
            claim.claimed_at,
        )

    @staticmethod
    def _workflow_lifecycle_release_bundle_row_values(
        row: Row,
    ) -> tuple[str, str, str, int, str, str, str]:
        return (
            str(row["transition_id"]),
            str(row["workflow_profile"]),
            str(row["route"]),
            int(row["revision"]),
            str(row["transition_action"]),
            str(row["payload"]),
            str(row["payload_sha256"]),
        )

    @classmethod
    def _verified_workflow_lifecycle_release_bundle_from_row(
        cls,
        row: Row | None,
    ) -> dict[str, object] | None:
        if row is None:
            return None
        payload = str(row["payload"])
        if sha256(payload.encode("utf-8")).hexdigest() != str(
            row["payload_sha256"]
        ):
            return None
        try:
            bundle = loads(payload)
        except (TypeError, ValueError):
            return None
        if not isinstance(bundle, dict):
            return None
        transition = bundle.get("transition")
        if not isinstance(transition, dict):
            return None
        if (
            transition.get("transition_id") != row["transition_id"]
            or transition.get("workflow_profile") != row["workflow_profile"]
            or transition.get("route") != row["route"]
            or transition.get("revision") != row["revision"]
            or transition.get("transition_action") != row["transition_action"]
        ):
            return None
        return bundle

    @staticmethod
    def _claim_from_row(row: Row | None) -> WorkflowVariantEvalRunClaim | None:
        if row is None:
            return None
        return WorkflowVariantEvalRunClaim(
            run_id=str(row["run_id"]),
            input_fingerprint=str(row["input_fingerprint"]),
            baseline_version_ref=str(row["baseline_version_ref"]),
            baseline_definition_hash=str(row["baseline_definition_hash"]),
            candidate_version_ref=str(row["candidate_version_ref"]),
            candidate_definition_hash=str(row["candidate_definition_hash"]),
            case_pack_id=str(row["case_pack_id"]),
            case_pack_version=str(row["case_pack_version"]),
            case_pack_fingerprint=str(row["case_pack_fingerprint"]),
            control_fingerprint=str(row["control_fingerprint"]),
            claimed_at=str(row["claimed_at"]),
        )

    def _verified_case_pack_from_row(
        self,
        row: Row | None,
    ) -> WorkflowVariantEvalCasePackContract | None:
        if row is None:
            return None
        payload = str(row["payload"])
        payload_sha256 = str(row["payload_sha256"])
        if sha256(payload.encode("utf-8")).hexdigest() != payload_sha256:
            return None
        try:
            case_pack = self._case_pack_from_payload(payload)
        except (KeyError, TypeError, ValueError):
            return None
        if (
            canonical_workflow_variant_eval_payload(case_pack) != payload
            or workflow_variant_eval_fingerprint(case_pack) != payload_sha256
            or validate_workflow_variant_eval_case_pack(case_pack)
            or case_pack.case_pack_id != str(row["case_pack_id"])
            or case_pack.case_pack_version != str(row["case_pack_version"])
            or case_pack.workflow_profile != str(row["workflow_profile"])
            or case_pack.route != str(row["route"])
            or case_pack.baseline_version_ref != str(row["baseline_version_ref"])
            or case_pack.candidate_version_ref != str(row["candidate_version_ref"])
            or str(case_pack.generated_at) != str(row["generated_at"])
        ):
            return None
        return case_pack

    def _verified_run_from_row(
        self,
        row: Row | None,
    ) -> WorkflowVariantEvalRunContract | None:
        if row is None:
            return None
        payload = str(row["payload"])
        payload_sha256 = str(row["payload_sha256"])
        if sha256(payload.encode("utf-8")).hexdigest() != payload_sha256:
            return None
        try:
            run = self._run_from_payload(payload)
        except (KeyError, TypeError, ValueError):
            return None
        case_pack = self.fetch_workflow_variant_case_pack(
            case_pack_id=run.case_pack_id,
            case_pack_version=run.case_pack_version,
        )
        if case_pack is None:
            return None
        claim = self.fetch_workflow_variant_eval_run_claim(run.run_id)
        baseline_hashes = set(run.baseline_definition_hashes)
        candidate_hashes = set(run.candidate_definition_hashes)
        if (
            claim is None
            or len(baseline_hashes) != 1
            or len(candidate_hashes) != 1
            or claim.case_pack_id != run.case_pack_id
            or claim.case_pack_version != run.case_pack_version
            or claim.case_pack_fingerprint != run.case_pack_fingerprint
            or claim.input_fingerprint
            != workflow_variant_eval_pack_input_fingerprint(case_pack)
            or claim.control_fingerprint
            != workflow_variant_eval_pack_control_fingerprint(case_pack)
            or claim.baseline_version_ref != run.baseline_version_ref
            or claim.candidate_version_ref != run.candidate_version_ref
            or claim.baseline_definition_hash not in baseline_hashes
            or claim.candidate_definition_hash not in candidate_hashes
        ):
            return None
        if (
            canonical_workflow_variant_eval_payload(run) != payload
            or workflow_variant_eval_fingerprint(run) != payload_sha256
            or validate_workflow_variant_eval_run(run, case_pack=case_pack)
            or run.run_id != str(row["run_id"])
            or run.case_pack_id != str(row["case_pack_id"])
            or run.case_pack_version != str(row["case_pack_version"])
            or run.case_pack_fingerprint != str(row["case_pack_fingerprint"])
            or run.workflow_profile != str(row["workflow_profile"])
            or run.route != str(row["route"])
            or run.baseline_version_ref != str(row["baseline_version_ref"])
            or run.candidate_version_ref != str(row["candidate_version_ref"])
            or str(run.generated_at) != str(row["generated_at"])
        ):
            return None
        return run

    @classmethod
    def _case_pack_from_payload(
        cls,
        payload: str,
    ) -> WorkflowVariantEvalCasePackContract:
        value = loads(payload)
        return WorkflowVariantEvalCasePackContract(
            **{
                **value,
                "cases": [cls._case_from_dict(case) for case in value["cases"]],
            }
        )

    @staticmethod
    def _control_from_dict(
        value: dict[str, object],
    ) -> WorkflowVariantEvalControlSnapshotContract:
        return WorkflowVariantEvalControlSnapshotContract(**value)

    @staticmethod
    def _observation_from_dict(
        value: dict[str, object],
    ) -> WorkflowVariantEvalObservationContract:
        return WorkflowVariantEvalObservationContract(**value)

    @classmethod
    def _case_from_dict(
        cls,
        value: dict[str, object],
    ) -> WorkflowVariantEvalCaseContract:
        return WorkflowVariantEvalCaseContract(
            **{
                **value,
                "control_snapshot": cls._control_from_dict(value["control_snapshot"]),
                "baseline_observation": cls._observation_from_dict(
                    value["baseline_observation"]
                ),
                "candidate_observation": cls._observation_from_dict(
                    value["candidate_observation"]
                ),
            }
        )

    @staticmethod
    def _case_result_from_dict(
        value: dict[str, object],
    ) -> WorkflowVariantEvalCaseResultContract:
        return WorkflowVariantEvalCaseResultContract(**value)

    @classmethod
    def _run_from_payload(cls, payload: str) -> WorkflowVariantEvalRunContract:
        value = loads(payload)
        return WorkflowVariantEvalRunContract(
            **{
                **value,
                "case_results": [
                    cls._case_result_from_dict(result)
                    for result in value["case_results"]
                ],
            }
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
