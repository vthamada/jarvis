from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from sqlite3 import IntegrityError, connect
from tempfile import gettempdir
from threading import Event
from uuid import uuid4

import pytest
from evolution_lab.service import (
    ComparisonInput,
    EvolutionLabService,
    FlowEvaluationInput,
    PostTaskReflectionInput,
    TechnologyAbsorptionInput,
)
from memory_service.service import MemoryService

from shared.contracts import (
    TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
    ExperienceRecordContract,
    OperatorFeedbackContract,
    PostTaskReflectionContract,
    ProceduralPlaybookCandidateContract,
    RecurringPatternEvidenceContract,
    SandboxToReleaseChecklistContract,
    SkillCandidateContract,
    SkillMiningRequestContract,
    TechnologyExperimentCaseContract,
    TechnologyExperimentControlSnapshotContract,
    TechnologyExperimentEvalRunClaimContract,
    TechnologyExperimentObservationContract,
    TechnologyExperimentPackContract,
    TechnologyRadarIntakeContract,
    WorkflowEvolutionRequestContract,
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
    WorkflowVariantEvalCaseContract,
    WorkflowVariantEvalCasePackContract,
    WorkflowVariantEvalControlSnapshotContract,
    WorkflowVariantEvalObservationContract,
    WorkflowVariantEvalRunContract,
)
from shared.domain_registry import (
    RUNTIME_ROUTE_REGISTRY,
    route_metadata_payload,
    workflow_definition_hash,
)
from shared.technology_experiment import (
    derive_technology_experiment_eval_run,
    technology_experiment_control_fingerprint,
    technology_experiment_pack_control_fingerprint,
    technology_experiment_pack_fingerprint,
    technology_experiment_pack_input_fingerprint,
    technology_experiment_text_fingerprint,
)
from shared.technology_radar_intake import (
    technology_radar_intake_fingerprint,
    technology_radar_review_subject_fingerprint,
)
from shared.types import MissionId, RiskLevel
from shared.workflow_variant_eval import (
    validate_workflow_variant_eval_run,
    workflow_variant_eval_case_pack_fingerprint,
    workflow_variant_eval_control_fingerprint,
)


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _technology_radar_intake(
    suffix: str,
    *,
    candidate_ref: str | None = None,
    intake_version: str = "1.0.0",
    source_locator: str | None = None,
    source_version_ref: str | None = None,
    source_kind: str = "repository",
    absorption_class: str = "reference",
    target_gap_refs: list[str] | None = None,
    recorded_at: str = "2026-08-12T10:02:00Z",
    previous: TechnologyRadarIntakeContract | None = None,
) -> TechnologyRadarIntakeContract:
    draft = TechnologyRadarIntakeContract(
        intake_id=f"technology-intake://radar/{suffix}/{intake_version}",
        candidate_ref=candidate_ref or f"technology-candidate://radar/{suffix}",
        intake_version=intake_version,
        technology_name=f"Reviewed Technology {suffix}",
        source_kind=source_kind,
        source_locator=source_locator or f"https://example.com/source/{suffix}",
        source_version_ref=(
            source_version_ref or f"source-version://radar/{suffix}"
        ),
        source_content_sha256="a" * 64,
        license_id="Apache-2.0",
        license_status="declared",
        license_evidence_ref=f"license-evidence://radar/{suffix}",
        retrieved_at="2026-08-12T10:00:00Z",
        claims=[f"claim {suffix}"],
        risks=[f"risk {suffix}"],
        absorption_class=absorption_class,
        target_gap_refs=target_gap_refs or ["KNW-006"],
        research_approval_ref=f"research-approval://radar/{suffix}",
        reviewed_payload_fingerprint="0" * 64,
        reviewer_ref="operator://technology-radar/reviewer",
        review_status="approved_for_radar_intake",
        review_evidence_refs=[f"review-evidence://radar/{suffix}"],
        reviewed_at="2026-08-12T10:01:00Z",
        recorded_at=recorded_at,
        previous_intake_id=previous.intake_id if previous else None,
        previous_intake_fingerprint=(
            technology_radar_intake_fingerprint(previous) if previous else None
        ),
    )
    return replace(
        draft,
        reviewed_payload_fingerprint=technology_radar_review_subject_fingerprint(
            draft
        ),
    )


def _reviewed_technology_radar_change(
    intake: TechnologyRadarIntakeContract,
    **changes: object,
) -> TechnologyRadarIntakeContract:
    draft = replace(
        intake,
        reviewed_payload_fingerprint="0" * 64,
        **changes,
    )
    return replace(
        draft,
        reviewed_payload_fingerprint=technology_radar_review_subject_fingerprint(
            draft
        ),
    )


def _technology_experiment_pack(
    suffix: str,
    *,
    intake: TechnologyRadarIntakeContract | None = None,
    generated_at: str = "2026-08-12T10:04:00Z",
) -> tuple[TechnologyRadarIntakeContract, TechnologyExperimentPackContract]:
    source = intake or _technology_radar_intake(
        suffix,
        absorption_class="sandbox_experiment",
    )
    pack_id = f"technology-experiment-pack://radar/{suffix}"
    pack_version = "1.0.0"
    case_id = f"technology-experiment-case://radar/{suffix}"
    input_fingerprint = "1" * 64
    baseline_definition_ref = "jarvis-baseline://typed-handoffs/v1"
    baseline_definition_hash = "4" * 64
    candidate_definition_ref = (
        "jarvis-experiment-definition://typed-handoffs/pattern-v1"
    )
    candidate_definition_hash = "5" * 64
    control = TechnologyExperimentControlSnapshotContract(
        control_snapshot_id=f"technology-experiment-control://radar/{suffix}",
        input_fingerprint=input_fingerprint,
        sandbox_policy_ref="technology-sandbox-policy://offline-attestation/v1",
        sandbox_policy_version="1.0.0",
        evaluator_version="1.0.0",
        deterministic_seed=208209,
        fixed_clock="2026-08-12T10:03:00Z",
        isolation_profile_ref=TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
        isolation_fingerprint="2" * 64,
        environment_fingerprint="3" * 64,
    )
    control_fingerprint = technology_experiment_control_fingerprint(control)

    def observation(
        arm: str,
        *,
        success: bool,
        rework_count: int,
    ) -> TechnologyExperimentObservationContract:
        is_baseline = arm == "baseline"
        return TechnologyExperimentObservationContract(
            observation_id=(
                f"technology-experiment-observation://radar/{suffix}/{arm}"
            ),
            experiment_pack_id=pack_id,
            pack_version=pack_version,
            case_id=case_id,
            case_version="1.0.0",
            arm=arm,
            definition_ref=(
                baseline_definition_ref
                if is_baseline
                else candidate_definition_ref
            ),
            definition_hash=(
                baseline_definition_hash
                if is_baseline
                else candidate_definition_hash
            ),
            input_fingerprint=input_fingerprint,
            control_snapshot_id=control.control_snapshot_id,
            control_snapshot_fingerprint=control_fingerprint,
            outcome_ref=f"technology-experiment-outcome://radar/{suffix}/{arm}",
            outcome_status="completed",
            contract_checks={"sovereign_consumer_preserved": True},
            isolation_checks={
                "dependencies_unchanged": True,
                "external_code_not_executed": True,
                "host_filesystem_unchanged": True,
                "network_disabled": True,
            },
            success_criteria_results={"boundary_is_explicit": success},
            action_count=4,
            rework_count=rework_count,
            evidence_refs=[
                f"evidence://technology-experiment/{suffix}/{arm}"
            ],
            limitations=[],
            observed_at=control.fixed_clock,
        )

    baseline = observation("baseline", success=False, rework_count=2)
    candidate = observation("candidate", success=True, rework_count=0)
    case = TechnologyExperimentCaseContract(
        experiment_pack_id=pack_id,
        pack_version=pack_version,
        case_id=case_id,
        case_version="1.0.0",
        scenario_ref=(
            f"technology-experiment-scenario://radar/{suffix}/bounded-delegation"
        ),
        input_fingerprint=input_fingerprint,
        baseline_definition_ref=baseline_definition_ref,
        baseline_definition_hash=baseline_definition_hash,
        candidate_definition_ref=candidate_definition_ref,
        candidate_definition_hash=candidate_definition_hash,
        critical_contract_check_refs=["sovereign_consumer_preserved"],
        critical_isolation_check_refs=[
            "dependencies_unchanged",
            "external_code_not_executed",
            "host_filesystem_unchanged",
            "network_disabled",
        ],
        success_criteria_refs=["boundary_is_explicit"],
        control_snapshot=control,
        baseline_observation=baseline,
        candidate_observation=candidate,
        evidence_refs=[
            f"evidence://technology-experiment/{suffix}/paired-case"
        ],
    )
    pack = TechnologyExperimentPackContract(
        experiment_pack_id=pack_id,
        pack_version=pack_version,
        intake_id=source.intake_id,
        intake_version=source.intake_version,
        intake_fingerprint=technology_radar_intake_fingerprint(source),
        reviewed_payload_fingerprint=source.reviewed_payload_fingerprint,
        candidate_ref=source.candidate_ref,
        technology_name=source.technology_name,
        source_content_sha256=source.source_content_sha256,
        absorption_class=source.absorption_class,
        translation_kind="absorbable_pattern",
        pattern_id=f"technology-pattern://radar/{suffix}/explicit-boundary",
        pattern_name="Explicit handoff boundary",
        pattern_summary="Translate explicit handoff typing into a bounded seam.",
        selected_claim_fingerprints=[
            technology_experiment_text_fingerprint(source.claims[0])
        ],
        selected_risk_fingerprints=[
            technology_experiment_text_fingerprint(source.risks[0])
        ],
        hypothesis="A typed boundary reduces rework without moving authority.",
        expected_gain="Fewer ambiguous delegation repairs in the same workflow.",
        sovereign_consumer_kind="jarvis_component",
        sovereign_consumer_ref="jarvis-component://planning-engine",
        consumer_contract_ref="jarvis-contract://deliberative-plan/v1",
        bounded_integration_seam="jarvis-seam://planning/handoff-description",
        target_gap_refs=list(source.target_gap_refs),
        baseline_definition_ref=baseline_definition_ref,
        baseline_definition_hash=baseline_definition_hash,
        candidate_definition_ref=candidate_definition_ref,
        candidate_definition_hash=candidate_definition_hash,
        isolation_profile_ref=TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
        risk_control_refs=["technology-risk-control://core-sovereignty"],
        mitigation_refs=["technology-mitigation://discard-inert-pack"],
        stop_condition_refs=["technology-stop-condition://any-regression"],
        license_id=source.license_id,
        license_status=source.license_status,
        license_evidence_ref=source.license_evidence_ref,
        rollback_plan_ref=f"technology-experiment-rollback://radar/{suffix}",
        rollback_steps=[
            "Discard the inert evidence and retain the baseline definition."
        ],
        rollback_verification_refs=[
            "technology-rollback-verification://baseline-unchanged"
        ],
        selection_review_ref=(
            f"technology-experiment-selection-review://radar/{suffix}/approved"
        ),
        selected_by_ref="operator://technology-experiment/reviewer-1",
        cases=[case],
        required_pass_rate=1.0,
        evidence_refs=[f"evidence://technology-experiment/{suffix}/pack-source"],
        generated_at=generated_at,
    )
    return source, pack


def _technology_experiment_claim(
    pack: TechnologyExperimentPackContract,
    *,
    run_id: str,
    claimed_at: str,
) -> TechnologyExperimentEvalRunClaimContract:
    return TechnologyExperimentEvalRunClaimContract(
        run_id=run_id,
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
        pack_fingerprint=technology_experiment_pack_fingerprint(pack),
        intake_id=pack.intake_id,
        intake_fingerprint=pack.intake_fingerprint,
        input_fingerprint=technology_experiment_pack_input_fingerprint(pack),
        control_fingerprint=technology_experiment_pack_control_fingerprint(pack),
        claimed_at=claimed_at,
    )


def _procedural_playbook_candidate(
    suffix: str = "001",
) -> ProceduralPlaybookCandidateContract:
    return ProceduralPlaybookCandidateContract(
        playbook_candidate_id=(
            f"playbook-candidate://software-change/{suffix}"
        ),
        procedure_name="bounded patch review",
        workflow_profile="software_change_workflow",
        route="software_engineering",
        domain="engenharia_de_software",
        bounded_steps=[
            "collect evidence",
            "run targeted tests",
            "prepare rollback",
        ],
        evidence_refs=[f"trace://req-playbook/{suffix}"],
        source_artifact_refs=["artifact://procedural/software/v1"],
        source_reflection_refs=["reflection://mission/001"],
        proposed_tests=["pytest tests/unit/test_memory_influence_policy.py"],
        rollback_plan_ref=f"rollback://playbook/{suffix}",
        timestamp="2026-07-18T23:10:00Z",
    )


def _playbook_release_gate(
    service: EvolutionLabService,
    proposal,  # type: ignore[no-untyped-def]
    decision,  # type: ignore[no-untyped-def]
):  # type: ignore[no-untyped-def]
    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=decision,
    )
    gate = service.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    return checklist, gate


def test_evolution_lab_service_name() -> None:
    assert EvolutionLabService.name == "evolution-lab"


def test_technology_radar_intake_store_is_versioned_idempotent_and_fail_closed() -> None:
    database_path = runtime_dir("technology-radar-store") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    first = _technology_radar_intake("001")

    assert service.register_technology_radar_intake(first) == first
    assert service.register_technology_radar_intake(first) == first
    assert service.list_recent_proposals() == []
    assert service.list_recent_decisions() == []
    restarted = EvolutionLabService(database_path=str(database_path))
    assert restarted.get_technology_radar_intake(intake_id=first.intake_id) == first
    assert restarted.get_technology_radar_intake(
        candidate_ref=first.candidate_ref,
        intake_version=first.intake_version,
    ) == first
    assert restarted.get_technology_radar_intake(
        candidate_ref=first.candidate_ref
    ) == first

    divergent = _reviewed_technology_radar_change(
        first,
        risks=[*first.risks, "divergent risk"],
    )
    with pytest.raises(ValueError, match="identity collision"):
        restarted.register_technology_radar_intake(divergent)
    duplicate_source = _technology_radar_intake(
        "002",
        source_locator=first.source_locator,
        source_version_ref=first.source_version_ref,
    )
    with pytest.raises(ValueError, match="identity collision"):
        restarted.register_technology_radar_intake(duplicate_source)

    unbound_revision = _technology_radar_intake(
        "003",
        candidate_ref=first.candidate_ref,
        intake_version="1.1.0",
    )
    with pytest.raises(ValueError, match="requires_predecessor"):
        restarted.register_technology_radar_intake(unbound_revision)
    revision = _technology_radar_intake(
        "004",
        candidate_ref=first.candidate_ref,
        intake_version="1.1.0",
        previous=first,
    )
    assert restarted.register_technology_radar_intake(revision) == revision
    assert restarted.get_technology_radar_intake(
        intake_id=revision.intake_id,
        candidate_ref=revision.candidate_ref,
        intake_version=revision.intake_version,
    ) == revision
    assert restarted.get_technology_radar_intake(
        candidate_ref=revision.candidate_ref
    ) is None
    assert restarted.get_technology_radar_intake(
        intake_id=revision.intake_id,
        candidate_ref="technology-candidate://radar/wrong",
    ) is None

    invalid_lineage = _reviewed_technology_radar_change(
        _technology_radar_intake(
            "005",
            candidate_ref=first.candidate_ref,
            intake_version="1.2.0",
            previous=revision,
        ),
        previous_intake_fingerprint="b" * 64,
    )
    with pytest.raises(ValueError, match="predecessor mismatch"):
        restarted.register_technology_radar_intake(invalid_lineage)

    with connect(database_path) as connection:
        connection.execute("DROP TRIGGER technology_radar_intakes_no_update")
        connection.execute(
            """
            UPDATE technology_radar_intakes
            SET payload_sha256 = ?
            WHERE intake_id = ?
            """,
            ("0" * 64, first.intake_id),
        )
        connection.commit()
    assert restarted.get_technology_radar_intake(
        intake_id=revision.intake_id
    ) is None


def test_technology_radar_intake_listing_filters_before_paging_and_skips_tamper() -> None:
    database_path = runtime_dir("technology-radar-list") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    first = _technology_radar_intake(
        "101",
        target_gap_refs=["KNW-006"],
        recorded_at="2026-08-12T10:02:00Z",
    )
    second = _technology_radar_intake(
        "102",
        source_kind="article",
        absorption_class="sandbox_experiment",
        target_gap_refs=["EVL-001"],
        recorded_at="2026-08-12T10:03:00Z",
    )
    newest = _technology_radar_intake(
        "103",
        target_gap_refs=["KNW-006"],
        recorded_at="2026-08-12T10:04:00Z",
    )
    for intake in (first, second, newest):
        service.register_technology_radar_intake(intake)

    assert service.list_technology_radar_intakes(
        source_kind="repository",
        absorption_class="reference",
        target_gap_ref="KNW-006",
        limit=1,
    ) == [newest]
    assert service.list_technology_radar_intakes(
        target_gap_ref="KNW-006",
        limit=1,
        offset=1,
    ) == [first]
    assert service.list_technology_radar_intakes(
        source_kind="article"
    ) == [second]

    with connect(database_path) as connection:
        for statement in (
            "UPDATE technology_radar_intakes SET source_kind = 'tampered'",
            "DELETE FROM technology_radar_intakes",
        ):
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(statement)
        connection.execute("DROP TRIGGER technology_radar_intakes_no_update")
        connection.execute(
            """
            UPDATE technology_radar_intakes
            SET payload_sha256 = ?
            WHERE intake_id = ?
            """,
            ("0" * 64, newest.intake_id),
        )
        connection.commit()

    assert service.get_technology_radar_intake(
        intake_id=newest.intake_id
    ) is None
    assert service.list_technology_radar_intakes(
        target_gap_ref="KNW-006",
        limit=1,
    ) == [first]
    with pytest.raises(ValueError, match="limit"):
        service.list_technology_radar_intakes(limit=0)
    with pytest.raises(ValueError, match="offset"):
        service.list_technology_radar_intakes(offset=-1)
    with pytest.raises(ValueError, match="source kind"):
        service.list_technology_radar_intakes(source_kind="unknown")
    with pytest.raises(ValueError, match="absorption class"):
        service.list_technology_radar_intakes(absorption_class="unknown")
    with pytest.raises(ValueError, match="version"):
        service.get_technology_radar_intake(
            candidate_ref=first.candidate_ref,
            intake_version="01.0.0",
        )


def test_technology_radar_intake_registration_is_atomic_under_concurrency() -> None:
    exact_service = EvolutionLabService(
        database_path=str(runtime_dir("technology-radar-exact-race") / "evolution.db")
    )
    exact = _technology_radar_intake("201")
    with ThreadPoolExecutor(max_workers=8) as executor:
        retries = list(
            executor.map(
                lambda _: exact_service.register_technology_radar_intake(exact),
                range(8),
            )
        )
    assert retries == [exact] * 8
    assert exact_service.list_technology_radar_intakes() == [exact]

    collision_service = EvolutionLabService(
        database_path=str(
            runtime_dir("technology-radar-genesis-race") / "evolution.db"
        )
    )
    variants = [
        _technology_radar_intake(
            f"30{index}",
            candidate_ref="technology-candidate://radar/concurrent",
        )
        for index in range(8)
    ]

    def register_variant(intake: TechnologyRadarIntakeContract) -> bool:
        try:
            collision_service.register_technology_radar_intake(intake)
        except ValueError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(register_variant, variants))
    assert results.count(True) == 1
    assert results.count(False) == 7
    assert len(collision_service.list_technology_radar_intakes()) == 1


def test_technology_radar_read_only_mode_does_not_create_an_absent_store() -> None:
    root = runtime_dir("technology-radar-read-only-absent")
    database_path = root / "missing-runtime" / "evolution.db"
    intake = _technology_radar_intake("401")

    assert not database_path.parent.exists()
    service = EvolutionLabService(
        database_path=str(database_path),
        read_only=True,
    )

    assert service.get_technology_radar_intake(
        intake_id=intake.intake_id
    ) is None
    assert service.list_technology_radar_intakes() == []
    assert not database_path.parent.exists()
    assert not database_path.exists()
    with pytest.raises(PermissionError, match="repository is read-only"):
        service.register_technology_radar_intake(intake)
    assert not database_path.parent.exists()


def test_technology_radar_read_only_mode_reads_without_sqlite_side_effects() -> None:
    root = runtime_dir("technology-radar-read-only-existing")
    database_path = root / "evolution.db"
    intake = _technology_radar_intake("402")
    writer = EvolutionLabService(database_path=str(database_path))
    writer.register_technology_radar_intake(intake)
    before_bytes = database_path.read_bytes()
    before_mtime = database_path.stat().st_mtime_ns
    before_entries = {path.name for path in root.iterdir()}

    reader = EvolutionLabService(
        database_path=str(database_path),
        read_only=True,
    )
    assert reader.get_technology_radar_intake(
        intake_id=intake.intake_id
    ) == intake
    assert reader.list_technology_radar_intakes(limit=1) == [intake]
    with pytest.raises(PermissionError, match="repository is read-only"):
        reader.register_technology_radar_intake(
            _technology_radar_intake("403")
        )

    assert database_path.read_bytes() == before_bytes
    assert database_path.stat().st_mtime_ns == before_mtime
    assert {path.name for path in root.iterdir()} == before_entries
    assert not (root / "evolution.db-wal").exists()
    assert not (root / "evolution.db-shm").exists()


def test_technology_radar_read_only_mode_observes_live_writer_commits() -> None:
    root = runtime_dir("technology-radar-read-only-live-writer")
    database_path = root / "evolution.db"
    writer = EvolutionLabService(database_path=str(database_path))
    reader = EvolutionLabService(
        database_path=str(database_path),
        read_only=True,
    )
    intake = _technology_radar_intake("404")
    writer_started = Event()

    def register_intake() -> TechnologyRadarIntakeContract:
        writer_started.set()
        return writer.register_technology_radar_intake(intake)

    with connect(database_path, timeout=30.0) as write_lock:
        write_lock.execute("BEGIN IMMEDIATE")
        locked_bytes = database_path.read_bytes()
        locked_mtime = database_path.stat().st_mtime_ns
        locked_entries = {path.name for path in root.iterdir()}
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending_write = executor.submit(register_intake)
            assert writer_started.wait(timeout=5.0)
            assert reader.list_technology_radar_intakes() == []
            assert not pending_write.done()
            assert database_path.read_bytes() == locked_bytes
            assert database_path.stat().st_mtime_ns == locked_mtime
            assert {path.name for path in root.iterdir()} == locked_entries
            write_lock.commit()
            assert pending_write.result(timeout=10.0) == intake

    committed_bytes = database_path.read_bytes()
    committed_mtime = database_path.stat().st_mtime_ns
    committed_entries = {path.name for path in root.iterdir()}
    assert reader.get_technology_radar_intake(
        intake_id=intake.intake_id
    ) == intake
    assert reader.list_technology_radar_intakes() == [intake]
    assert database_path.read_bytes() == committed_bytes
    assert database_path.stat().st_mtime_ns == committed_mtime
    assert {path.name for path in root.iterdir()} == committed_entries
    assert not (root / "evolution.db-wal").exists()
    assert not (root / "evolution.db-shm").exists()


def test_technology_radar_read_only_mode_treats_legacy_schema_as_empty() -> None:
    root = runtime_dir("technology-radar-read-only-legacy")
    database_path = root / "evolution.db"
    with connect(database_path) as connection:
        connection.execute("CREATE TABLE legacy_state (id TEXT PRIMARY KEY)")
    before_bytes = database_path.read_bytes()
    before_entries = {path.name for path in root.iterdir()}

    reader = EvolutionLabService(
        database_path=str(database_path),
        read_only=True,
    )
    assert reader.get_technology_radar_intake(
        intake_id="technology-intake://radar/missing/1.0.0"
    ) is None
    assert reader.list_technology_radar_intakes() == []
    assert database_path.read_bytes() == before_bytes
    assert {path.name for path in root.iterdir()} == before_entries


def test_technology_experiment_pack_store_binds_exact_intake_and_restarts() -> None:
    database_path = runtime_dir("technology-experiment-pack-store") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    intake, pack = _technology_experiment_pack("pack-store")

    with pytest.raises(ValueError, match="verified radar intake"):
        service.register_technology_experiment_pack(pack)
    service.register_technology_radar_intake(intake)
    assert service.register_technology_experiment_pack(pack) == pack
    assert service.register_technology_experiment_pack(pack) == pack
    assert service.list_recent_proposals() == []
    assert service.list_recent_decisions() == []

    restarted = EvolutionLabService(database_path=str(database_path))
    assert restarted.get_technology_experiment_pack(
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
    ) == pack
    assert restarted.list_technology_experiment_packs(
        intake_id=intake.intake_id,
        candidate_ref=intake.candidate_ref,
        absorption_class=intake.absorption_class,
        sovereign_consumer_ref=pack.sovereign_consumer_ref,
        pattern_id=pack.pattern_id,
        target_gap_ref="KNW-006",
    ) == [pack]
    with pytest.raises(ValueError, match="identity collision"):
        restarted.register_technology_experiment_pack(
            replace(pack, hypothesis="A different but otherwise valid hypothesis.")
        )
    with pytest.raises(ValueError, match="does not match the verified intake"):
        restarted.register_technology_experiment_pack(
            replace(pack, intake_fingerprint="f" * 64)
        )
    with pytest.raises(ValueError, match="between 1 and 500"):
        restarted.list_technology_experiment_packs(limit=0)
    with pytest.raises(ValueError, match="non-negative"):
        restarted.list_technology_experiment_packs(offset=-1)
    with pytest.raises(ValueError, match="canonical"):
        restarted.get_technology_experiment_pack(
            experiment_pack_id=pack.experiment_pack_id,
            pack_version="01.0.0",
        )


def test_technology_experiment_pack_store_is_append_only_tamper_evident_and_fair() -> None:
    database_path = runtime_dir("technology-experiment-pack-tamper") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    first_intake, first = _technology_experiment_pack("pack-first")
    second_intake, second = _technology_experiment_pack(
        "pack-second",
        generated_at="2026-08-12T10:05:00Z",
    )
    for intake, pack in ((first_intake, first), (second_intake, second)):
        service.register_technology_radar_intake(intake)
        service.register_technology_experiment_pack(pack)

    with connect(database_path) as connection:
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE technology_experiment_packs SET pattern_id = 'tampered'"
            )
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute("DELETE FROM technology_experiment_packs")
        connection.execute("DROP TRIGGER technology_experiment_packs_no_update")
        connection.execute(
            """
            UPDATE technology_experiment_packs
            SET payload_sha256 = ?
            WHERE experiment_pack_id = ? AND pack_version = ?
            """,
            ("0" * 64, second.experiment_pack_id, second.pack_version),
        )
        connection.commit()

    assert service.get_technology_experiment_pack(
        experiment_pack_id=second.experiment_pack_id,
        pack_version=second.pack_version,
    ) is None
    assert service.list_technology_experiment_packs(limit=1) == [first]


def test_technology_experiment_pack_registration_is_atomic_under_concurrency() -> None:
    exact_service = EvolutionLabService(
        database_path=str(
            runtime_dir("technology-experiment-pack-concurrency") / "evolution.db"
        )
    )
    intake, pack = _technology_experiment_pack("pack-concurrency")
    exact_service.register_technology_radar_intake(intake)
    with ThreadPoolExecutor(max_workers=8) as executor:
        retries = list(
            executor.map(
                lambda _: exact_service.register_technology_experiment_pack(pack),
                range(8),
            )
        )
    assert retries == [pack] * 8
    assert exact_service.list_technology_experiment_packs() == [pack]

    collision_service = EvolutionLabService(
        database_path=str(
            runtime_dir("technology-experiment-pack-collision") / "evolution.db"
        )
    )
    collision_service.register_technology_radar_intake(intake)
    variants = [
        replace(pack, hypothesis=f"Valid bounded hypothesis variant {index}.")
        for index in range(8)
    ]

    def register_variant(candidate: TechnologyExperimentPackContract) -> bool:
        try:
            collision_service.register_technology_experiment_pack(candidate)
        except ValueError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(register_variant, variants))
    assert results.count(True) == 1
    assert results.count(False) == 7
    assert len(collision_service.list_technology_experiment_packs()) == 1


def test_technology_experiment_claim_and_run_are_concurrency_safe_and_recoverable() -> None:
    database_path = runtime_dir("technology-experiment-eval-store") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    intake, pack = _technology_experiment_pack("eval-store")
    service.register_technology_radar_intake(intake)
    service.register_technology_experiment_pack(pack)
    run_id = "technology-experiment-run://radar/eval-store/run-1"
    generated_at = "2026-08-12T10:05:00Z"
    claim = _technology_experiment_claim(
        pack,
        run_id=run_id,
        claimed_at=generated_at,
    )
    run = derive_technology_experiment_eval_run(
        run_id=run_id,
        pack=pack,
        intake=intake,
        generated_at=generated_at,
    )

    with ThreadPoolExecutor(max_workers=8) as executor:
        claim_results = list(
            executor.map(
                lambda _: service.claim_technology_experiment_eval_run(claim),
                range(8),
            )
        )
    assert claim_results.count(True) == 1
    assert claim_results.count(False) == 7
    with ThreadPoolExecutor(max_workers=8) as executor:
        run_results = list(
            executor.map(
                lambda _: service.record_technology_experiment_eval_run(run),
                range(8),
            )
        )
    assert run_results == [run] * 8

    restarted = EvolutionLabService(database_path=str(database_path))
    assert restarted.get_technology_experiment_eval_run(run_id=run_id) == run
    assert restarted.list_technology_experiment_eval_runs(
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
        intake_id=intake.intake_id,
        candidate_ref=intake.candidate_ref,
        pattern_id=pack.pattern_id,
        sovereign_consumer_ref=pack.sovereign_consumer_ref,
        status="passed_sandbox_only",
    ) == [run]
    with pytest.raises(ValueError, match="run id collision"):
        restarted.claim_technology_experiment_eval_run(
            replace(claim, claimed_at="2026-08-12T10:06:00Z")
        )
    divergent_run = derive_technology_experiment_eval_run(
        run_id=run_id,
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T10:06:00Z",
    )
    with pytest.raises(ValueError, match="run id collision"):
        restarted.record_technology_experiment_eval_run(divergent_run)

    orphan_run_id = "technology-experiment-run://radar/eval-store/orphan"
    orphan_time = "2026-08-12T10:07:00Z"
    orphan_claim = _technology_experiment_claim(
        pack,
        run_id=orphan_run_id,
        claimed_at=orphan_time,
    )
    assert restarted.claim_technology_experiment_eval_run(orphan_claim)
    after_interruption = EvolutionLabService(database_path=str(database_path))
    assert not after_interruption.claim_technology_experiment_eval_run(orphan_claim)
    orphan_run = derive_technology_experiment_eval_run(
        run_id=orphan_run_id,
        pack=pack,
        intake=intake,
        generated_at=orphan_time,
    )
    assert after_interruption.record_technology_experiment_eval_run(orphan_run) == (
        orphan_run
    )

    early_run_id = "technology-experiment-run://radar/eval-store/predates-claim"
    early_run = derive_technology_experiment_eval_run(
        run_id=early_run_id,
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T10:08:00Z",
    )
    late_claim = _technology_experiment_claim(
        pack,
        run_id=early_run_id,
        claimed_at="2026-08-12T10:09:00Z",
    )
    assert after_interruption.claim_technology_experiment_eval_run(late_claim)
    with pytest.raises(ValueError, match="cannot predate its immutable claim"):
        after_interruption.record_technology_experiment_eval_run(early_run)
    assert after_interruption.get_technology_experiment_eval_run(
        run_id=early_run_id
    ) is None
    assert after_interruption.list_recent_proposals() == []
    assert after_interruption.list_recent_decisions() == []


def test_technology_experiment_eval_store_is_append_only_tamper_evident_and_fair() -> None:
    database_path = runtime_dir("technology-experiment-eval-tamper") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    intake, pack = _technology_experiment_pack("eval-tamper")
    service.register_technology_radar_intake(intake)
    service.register_technology_experiment_pack(pack)
    runs = []
    for suffix, generated_at in (
        ("first", "2026-08-12T10:05:00Z"),
        ("second", "2026-08-12T10:06:00Z"),
    ):
        run_id = f"technology-experiment-run://radar/eval-tamper/{suffix}"
        claim = _technology_experiment_claim(
            pack,
            run_id=run_id,
            claimed_at=generated_at,
        )
        run = derive_technology_experiment_eval_run(
            run_id=run_id,
            pack=pack,
            intake=intake,
            generated_at=generated_at,
        )
        assert service.claim_technology_experiment_eval_run(claim)
        service.record_technology_experiment_eval_run(run)
        runs.append(run)

    with connect(database_path) as connection:
        for table in (
            "technology_experiment_eval_run_claims",
            "technology_experiment_eval_runs",
        ):
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(f"UPDATE {table} SET payload_sha256 = 'tampered'")
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(f"DELETE FROM {table}")
        connection.execute("DROP TRIGGER technology_experiment_eval_runs_no_update")
        connection.execute(
            """
            UPDATE technology_experiment_eval_runs
            SET payload_sha256 = ?
            WHERE run_id = ?
            """,
            ("0" * 64, runs[1].run_id),
        )
        connection.commit()

    assert service.get_technology_experiment_eval_run(
        run_id=runs[1].run_id
    ) is None
    assert service.list_technology_experiment_eval_runs(limit=1) == [runs[0]]
    with pytest.raises(ValueError, match="evaluation status"):
        service.list_technology_experiment_eval_runs(status="promoted")

    with connect(database_path) as connection:
        connection.execute("DROP TRIGGER technology_radar_intakes_no_update")
        connection.execute(
            """
            UPDATE technology_radar_intakes
            SET payload_sha256 = ?
            WHERE intake_id = ?
            """,
            ("f" * 64, intake.intake_id),
        )
        connection.commit()
    assert service.get_technology_experiment_pack(
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
    ) is None
    assert service.list_technology_experiment_packs() == []
    assert service.get_technology_experiment_eval_run(run_id=runs[0].run_id) is None
    assert service.list_technology_experiment_eval_runs() == []


def test_technology_experiment_read_only_missing_store_has_no_side_effects() -> None:
    root = runtime_dir("technology-experiment-read-only-absent")
    database_path = root / "missing-runtime" / "evolution.db"
    intake, pack = _technology_experiment_pack("read-only")
    run_id = "technology-experiment-run://radar/read-only/run-1"
    run = derive_technology_experiment_eval_run(
        run_id=run_id,
        pack=pack,
        intake=intake,
        generated_at="2026-08-12T10:05:00Z",
    )
    claim = _technology_experiment_claim(
        pack,
        run_id=run_id,
        claimed_at="2026-08-12T10:05:00Z",
    )
    reader = EvolutionLabService(
        database_path=str(database_path),
        read_only=True,
    )

    assert reader.get_technology_experiment_pack(
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
    ) is None
    assert reader.list_technology_experiment_packs() == []
    assert reader.get_technology_experiment_eval_run(run_id=run_id) is None
    assert reader.list_technology_experiment_eval_runs() == []
    for writer in (
        lambda: reader.register_technology_experiment_pack(pack),
        lambda: reader.claim_technology_experiment_eval_run(claim),
        lambda: reader.record_technology_experiment_eval_run(run),
    ):
        with pytest.raises(PermissionError, match="repository is read-only"):
            writer()
    assert not database_path.parent.exists()
    assert not database_path.exists()


def test_technology_experiment_read_only_store_reads_without_sqlite_side_effects() -> None:
    root = runtime_dir("technology-experiment-read-only-existing")
    database_path = root / "evolution.db"
    writer = EvolutionLabService(database_path=str(database_path))
    intake, pack = _technology_experiment_pack("read-only-existing")
    writer.register_technology_radar_intake(intake)
    writer.register_technology_experiment_pack(pack)
    run_id = "technology-experiment-run://radar/read-only-existing/run-1"
    generated_at = "2026-08-12T10:05:00Z"
    claim = _technology_experiment_claim(
        pack,
        run_id=run_id,
        claimed_at=generated_at,
    )
    run = derive_technology_experiment_eval_run(
        run_id=run_id,
        pack=pack,
        intake=intake,
        generated_at=generated_at,
    )
    writer.claim_technology_experiment_eval_run(claim)
    writer.record_technology_experiment_eval_run(run)
    before_bytes = database_path.read_bytes()
    before_mtime = database_path.stat().st_mtime_ns
    before_entries = {path.name for path in root.iterdir()}

    reader = EvolutionLabService(database_path=str(database_path), read_only=True)
    assert reader.get_technology_experiment_pack(
        experiment_pack_id=pack.experiment_pack_id,
        pack_version=pack.pack_version,
    ) == pack
    assert reader.list_technology_experiment_packs() == [pack]
    assert reader.get_technology_experiment_eval_run(run_id=run_id) == run
    assert reader.list_technology_experiment_eval_runs() == [run]
    with pytest.raises(PermissionError, match="repository is read-only"):
        reader.claim_technology_experiment_eval_run(claim)

    assert database_path.read_bytes() == before_bytes
    assert database_path.stat().st_mtime_ns == before_mtime
    assert {path.name for path in root.iterdir()} == before_entries
    assert not (root / "evolution.db-wal").exists()
    assert not (root / "evolution.db-shm").exists()


def test_technology_experiment_read_only_legacy_schema_is_empty() -> None:
    root = runtime_dir("technology-experiment-read-only-legacy")
    database_path = root / "evolution.db"
    with connect(database_path) as connection:
        connection.execute("CREATE TABLE legacy_state (id TEXT PRIMARY KEY)")
    before_bytes = database_path.read_bytes()
    before_entries = {path.name for path in root.iterdir()}

    reader = EvolutionLabService(database_path=str(database_path), read_only=True)
    assert reader.get_technology_experiment_pack(
        experiment_pack_id="technology-experiment-pack://radar/missing",
        pack_version="1.0.0",
    ) is None
    assert reader.list_technology_experiment_packs() == []
    assert reader.get_technology_experiment_eval_run(
        run_id="technology-experiment-run://radar/missing"
    ) is None
    assert reader.list_technology_experiment_eval_runs() == []
    assert database_path.read_bytes() == before_bytes
    assert {path.name for path in root.iterdir()} == before_entries


def test_evolution_lab_defaults_to_manual_variants_strategy() -> None:
    temp_dir = runtime_dir("evolution-lab-default-strategy")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    assert service.preferred_strategy() == "manual_variants"
    assert service.resolve_strategy_name(None) == "manual_variants"
    assert service.resolve_strategy_name("unknown") == "manual_variants"
    assert "manual_variants" in service.list_supported_strategies()


def test_evolution_lab_exposes_inactive_workflow_version_registry() -> None:
    temp_dir = runtime_dir("evolution-lab-workflow-version-registry")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    registry = service.build_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:00:00Z",
        evidence_refs=["evidence://evolution-lab/workflow-baseline"],
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "operational_readiness_workflow"
    )
    candidate_steps = [*baseline.workflow_steps, "record candidate evidence"]
    candidate: WorkflowProfileVersionContract = replace(
        baseline,
        workflow_version_id=(
            "workflow-version://operational_readiness_workflow/1.1.0"
        ),
        version="1.1.0",
        lifecycle_status="candidate_inactive",
        definition_hash=workflow_definition_hash(
            workflow_steps=candidate_steps,
            workflow_checkpoints=baseline.workflow_checkpoints,
            workflow_decision_points=baseline.workflow_decision_points,
            success_criteria=baseline.success_criteria,
        ),
        workflow_steps=candidate_steps,
        evidence_refs=[*baseline.evidence_refs, "pattern://readiness/evidence"],
        proposed_tests=["test://workflow/readiness-candidate"],
        rollback_plan_ref="rollback://workflow/readiness/1.0.0",
        baseline_version_ref=baseline.workflow_version_id,
        change_summary="record evidence before readiness recommendation",
        risk_level="moderate",
        review_status="needs_review",
        runtime_binding_status="inactive_candidate",
        human_review_required=True,
        sandbox_required=True,
    )

    updated = service.register_workflow_candidate_version(registry, candidate)

    assert "evolution-lab://workflow-version-registry" in registry.evidence_refs
    assert updated.candidate_count == 1
    assert updated.versions[-1].lifecycle_status == "candidate_inactive"
    assert updated.versions[-1].runtime_activation_allowed is False
    assert updated.active_registry_mutation_allowed is False
    assert updated.automatic_promotion_allowed is False


def test_reviewed_memory_pattern_builds_only_inactive_workflow_candidate_end_to_end() -> None:
    temp_dir = runtime_dir("evolution-lab-workflow-candidate")
    memory = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    for index in (1, 2):
        experience_id = f"experience://workflow-candidate/{index}"
        memory.record_experience_reflection(
            experience=ExperienceRecordContract(
                experience_id=experience_id,
                mission_id=MissionId(f"mission-workflow-candidate-{index}"),
                workflow_profile="software_change_workflow",
                route="software_development",
                primary_domain_driver="software_engineering",
                outcome_status="completed",
                checkpoints=["run_targeted_tests", "record_release_evidence"],
                evidence_refs=[f"trace://workflow-candidate/{index}"],
                timestamp=f"2026-07-16T18:00:0{index}Z",
            ),
            reflection=PostTaskReflectionContract(
                reflection_id=f"reflection://workflow-candidate/{index}",
                experience_id=experience_id,
                reflection_status="candidate",
                learning_candidate="release evidence should be explicit",
                recommendation="review a bounded release evidence checkpoint",
                evidence_refs=[f"trace://workflow-candidate/{index}"],
                timestamp=f"2026-07-16T18:01:0{index}Z",
            ),
        )
    report = memory.build_recurring_pattern_report(
        report_id="recurring-pattern-report://workflow-candidate",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        generated_at="2026-07-16T18:10:00Z",
    )
    pattern = report.patterns[0]
    registry = service.build_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:15:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == pattern.workflow_profile
    )
    proposal = service.create_workflow_pattern_review_proposal(
        pattern=pattern,
        baseline=baseline,
        proposed_tests=["test://workflow/software-change-candidate"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-reviewer",
        evidence_refs=["evidence://workflow/software-change/review"],
        proposed_tests=["test://workflow/software-change-candidate"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    request = WorkflowEvolutionRequestContract(
        workflow_evolution_request_id=(
            "workflow-evolution-request://software-change/1.1.0"
        ),
        source_pattern_ref=pattern.pattern_id,
        source_review_decision_id=decision.review_decision_id,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version="1.1.0",
        step_additions=["record verified release evidence"],
        step_removals=[],
        checkpoint_additions=["release_evidence_recorded"],
        checkpoint_removals=[],
        decision_point_additions=["release_evidence_gate"],
        decision_point_removals=[],
        success_criteria_additions=["release evidence remains auditable"],
        success_criteria_removals=[],
        change_summary="record evidence before the release recommendation",
        evidence_refs=["evidence://workflow/software-change/review"],
        proposed_tests=["test://workflow/software-change-candidate"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
        risk_level="moderate",
        timestamp="2026-07-16T18:20:00Z",
    )
    active_before = {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    }

    result = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=decision,
        request=request,
    )
    assert result.candidate is not None
    updated = service.register_workflow_candidate_version(
        registry,
        result.candidate,
    )

    assert report.report_status == "evidence_ready_for_human_review"
    assert decision.review_status == "sandboxed"
    assert result.build_status == "candidate_created_inactive"
    assert result.blockers == []
    assert result.delta_summary["step_additions"] == [
        "record verified release evidence"
    ]
    assert result.candidate.lifecycle_status == "candidate_inactive"
    assert result.candidate.review_status == "needs_review"
    assert result.candidate.runtime_binding_status == "inactive_candidate"
    assert result.candidate.active_registry_write_allowed is False
    assert result.candidate.runtime_activation_allowed is False
    assert result.candidate.automatic_promotion_allowed is False
    assert updated.candidate_count == 1
    assert registry.candidate_count == 0
    assert {
        route: route_metadata_payload(route) for route in RUNTIME_ROUTE_REGISTRY
    } == active_before


def test_workflow_candidate_builder_blocks_forgery_invalid_delta_and_authority() -> None:
    temp_dir = runtime_dir("evolution-lab-workflow-candidate-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    registry = service.build_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-07-16T18:15:00Z",
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://workflow-builder-blocked",
        pattern_type="repeated_successful_workflow",
        pattern_status="evidence_ready_for_human_review",
        workflow_profile=baseline.workflow_profile,
        route=baseline.route,
        domain="software_engineering",
        occurrence_count=2,
        minimum_occurrences=2,
        successful_occurrences=2,
        non_successful_occurrences=0,
        confidence_status="bounded_moderate",
        outcome_summary="completed=2",
        pattern_summary="two compatible completed experiences",
        experience_refs=["experience://workflow/1", "experience://workflow/2"],
        reflection_refs=["reflection://workflow/1", "reflection://workflow/2"],
        feedback_refs=[],
        evidence_refs=["trace://workflow/1", "trace://workflow/2"],
        recurring_signals=["record_release_evidence"],
        conflict_flags=[],
        blockers=[],
        generated_at="2026-07-16T18:10:00Z",
    )
    proposal = service.create_workflow_pattern_review_proposal(
        pattern=pattern,
        baseline=baseline,
        proposed_tests=["test://workflow/builder-blocked"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-reviewer",
        evidence_refs=["evidence://workflow/builder-blocked"],
        proposed_tests=["test://workflow/builder-blocked"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
    )
    request = WorkflowEvolutionRequestContract(
        workflow_evolution_request_id="workflow-evolution-request://blocked/1.1.0",
        source_pattern_ref=pattern.pattern_id,
        source_review_decision_id=decision.review_decision_id,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version="1.1.0",
        step_additions=["record verified release evidence"],
        step_removals=[],
        checkpoint_additions=[],
        checkpoint_removals=[],
        decision_point_additions=[],
        decision_point_removals=[],
        success_criteria_additions=[],
        success_criteria_removals=[],
        change_summary="record release evidence",
        evidence_refs=["evidence://workflow/builder-blocked"],
        proposed_tests=["test://workflow/builder-blocked"],
        rollback_plan_ref="rollback://workflow/software-change/1.0.0",
        risk_level="moderate",
        timestamp="2026-07-16T18:20:00Z",
    )

    forged_decision = replace(
        decision,
        review_decision_id="review-decision://forged",
    )
    forged = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=forged_decision,
        request=replace(
            request,
            source_review_decision_id=forged_decision.review_decision_id,
        ),
    )
    invalid_delta = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=decision,
        request=replace(
            request,
            step_additions=[],
            step_removals=["missing baseline step"],
        ),
    )
    unsafe = service.build_workflow_candidate_from_reviewed_pattern(
        pattern=pattern,
        baseline=baseline,
        review_decision=decision,
        request=replace(request, active_registry_write_allowed=True),
    )

    assert forged.candidate is None
    assert "persisted_human_review_decision_required" in forged.blockers
    assert invalid_delta.candidate is None
    assert "steps_removal_not_in_baseline" in invalid_delta.blockers
    assert unsafe.candidate is None
    assert "workflow_request_authority_claim_not_allowed" in unsafe.blockers


def test_evolution_lab_persists_proposals_and_sandbox_candidate_decision() -> None:
    temp_dir = runtime_dir("evolution-lab")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="workflow_refinement",
        target_scope="orchestrator-service",
        hypothesis="Candidate sequencing should improve stability without increasing risk.",
        expected_gain="Higher stability for the same low-risk profile.",
        baseline_refs=["baseline://orchestrator/current"],
        source_signals=["observability://flows/req-1"],
        proposed_tests=["pytest -q"],
    )

    comparison = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="current",
            candidate_label="candidate-a",
            baseline_metrics={"stability": 0.72, "risk": 0.2, "throughput": 0.5},
            candidate_metrics={"stability": 0.81, "risk": 0.18, "throughput": 0.56},
            governance_refs=["policy://sandbox/manual-review"],
            notes=["candidate kept sandbox-only"],
        ),
    )

    assert comparison.decision.decision == "sandbox_candidate"
    assert comparison.decision.promoted_to is None
    assert comparison.metric_deltas["stability"] > 0
    assert "strategy://manual_variants" in proposal.source_signals
    assert "preferred_strategy=manual_variants" in proposal.promotion_constraints
    assert proposal.selection_criteria == {}
    assert proposal.evaluation_matrix == {}
    assert "strategy=manual_variants" in comparison.decision.notes
    assert comparison.decision.selection_criteria["strategy"] == "manual_variants"
    assert comparison.decision.metric_deltas["stability"] > 0
    assert service.list_recent_proposals(limit=1)[0].target_scope == "orchestrator-service"
    assert service.list_recent_decisions(limit=1)[0].decision == "sandbox_candidate"


def test_evolution_lab_holds_baseline_when_risk_increases() -> None:
    temp_dir = runtime_dir("evolution-lab-hold")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="prompt_refinement",
        target_scope="synthesis-engine",
        hypothesis="A more aggressive style could improve throughput.",
        expected_gain="Faster synthesis.",
        baseline_refs=["baseline://synthesis/current"],
        strategy_name="textgrad_like_refinement",
    )

    comparison = service.compare_candidate(
        proposal,
        ComparisonInput(
            baseline_label="current",
            candidate_label="candidate-risky",
            baseline_metrics={"stability": 0.8, "risk": 0.1},
            candidate_metrics={"stability": 0.78, "risk": 0.3},
            governance_refs=["policy://sandbox/manual-review"],
            notes=["candidate rejected for higher risk"],
            strategy_name="textgrad_like_refinement",
        ),
    )

    assert comparison.decision.decision == "hold_baseline"
    assert comparison.decision.rollback_plan_ref == "sandbox://rollback/current"
    assert "strategy://textgrad_like_refinement" in proposal.source_signals
    assert "strategy=textgrad_like_refinement" in comparison.decision.notes


def test_evolution_lab_registers_governed_technology_absorption_candidate() -> None:
    temp_dir = runtime_dir("evolution-lab-technology-absorption")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_technology_absorption_candidate(
        TechnologyAbsorptionInput(
            candidate_ref="tech-candidate://openai-agents-sdk/handoff-adapters",
            technology_name="OpenAI Agents SDK",
            absorption_class="promotable_translation",
            target_gap_refs=["TA-005"],
            hypothesis="Handoff adapter semantics can improve bounded edge tracing.",
            expected_gain="Clearer handoff evidence without replacing the core.",
            source_refs=["source://technology-absorption-order/openai-agents-sdk"],
            evidence_refs=["evidence://comparison/handoff-adapter"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            risk_hint="moderate",
            status="validated",
            requested_core_role="adapter",
            rollback_plan_ref="rollback://sovereign-core/current",
        ),
        target_scope="orchestrator-service",
    )

    state = proposal.strategy_context["technology_absorption_state"]
    matrix = proposal.evaluation_matrix["technology_absorption"]

    assert proposal.proposal_type == "technology_absorption_candidate"
    assert proposal.requires_sandbox is True
    assert proposal.candidate_refs == [
        "tech-candidate://openai-agents-sdk/handoff-adapters"
    ]
    assert state["absorption_decision"] == "manual_promotion_review"
    assert state["promotion_readiness"] == "manual_review_only"
    assert matrix["absorption_class"] == "promotable_translation"
    assert matrix["blockers"] == []
    assert "technology://readiness/ready_for_manual_review" in proposal.source_signals
    assert proposal.strategy_context["promotion_policy"]["automatic_promotion"] is False
    assert service.list_recent_proposals(limit=1)[0].target_scope == "orchestrator-service"


def test_evolution_lab_blocks_technology_candidate_that_requests_core_role() -> None:
    temp_dir = runtime_dir("evolution-lab-technology-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_technology_absorption_candidate(
        TechnologyAbsorptionInput(
            candidate_ref="tech-candidate://external-core",
            technology_name="External Core Runtime",
            absorption_class="sandbox_experiment",
            target_gap_refs=["RH-001"],
            hypothesis="External runtime could replace central reasoning.",
            expected_gain="Not accepted because it violates core sovereignty.",
            evidence_refs=["evidence://claim"],
            proposed_tests=["pytest tests/unit"],
            requested_core_role="core_brain",
            rollback_plan_ref="rollback://baseline",
        )
    )

    state = proposal.strategy_context["technology_absorption_state"]
    assert state["absorption_decision"] == "block_absorption"
    assert state["promotion_readiness"] == "blocked"
    assert "technology://blocker/core_sovereignty_violation" in proposal.source_signals
    assert proposal.strategy_context["promotion_policy"]["core_replacement_allowed"] is False


def test_evolution_lab_creates_sandbox_proposal_from_post_task_reflection() -> None:
    temp_dir = runtime_dir("evolution-lab-reflection")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reflection/001",
            mission_id="mission-reflection",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Contract-first slices reduced implementation drift.",
            recommendation="Promote a bounded checklist only after tests.",
            evidence_refs=["trace://req-reflection"],
            signal_refs=["workflow_output_status:coherent"],
            proposed_change_type="workflow",
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/current",
        )
    )

    assert proposal.proposal_type == "post_task_reflection_improvement"
    assert proposal.requires_sandbox is True
    assert proposal.optimization_candidate_status == "candidate"
    assert proposal.strategy_context["promotion_policy"]["automatic_promotion"] is False
    assert proposal.strategy_context["promotion_policy"]["core_mutation_allowed"] is False
    assert proposal.strategy_context["evolution_review"]["review_status"] == "needs_review"
    assert (
        proposal.strategy_context["evolution_review"]["promotion_blocked_without_gate"]
        is True
    )
    assert proposal.evaluation_matrix["post_task_reflection"]["reflection_status"] == (
        "candidate"
    )
    review_items = service.list_human_review_queue(limit=5)
    assert review_items[0].review_status == "needs_review"
    assert review_items[0].requires_human_review is True
    assert review_items[0].requires_sandbox is True
    assert review_items[0].rollback_plan_ref == "rollback://workflow/current"
    assert "experience://mission-reflection/001" in review_items[0].candidate_refs


def test_evolution_lab_creates_review_only_proposal_from_operator_feedback() -> None:
    temp_dir = runtime_dir("evolution-lab-operator-feedback")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    experience = ExperienceRecordContract(
        experience_id="experience://mission-feedback/001",
        mission_id="mission-feedback",
        workflow_profile="software_change_workflow",
        outcome_status="completed",
        route="software_development",
        primary_domain_driver="engenharia_de_software",
        evidence_refs=["trace://mission-feedback"],
        timestamp="2026-07-16T00:00:00+00:00",
    )
    reflection = PostTaskReflectionContract(
        reflection_id="reflection://mission-feedback/001",
        experience_id=experience.experience_id,
        reflection_status="candidate",
        learning_candidate="Use explicit release evidence.",
        recommendation="Keep the candidate sandboxed for review.",
        evidence_refs=["trace://mission-feedback"],
        rollback_plan_ref="rollback://mission-feedback/current",
        timestamp="2026-07-16T00:00:01+00:00",
    )
    feedback = OperatorFeedbackContract(
        feedback_id="operator-feedback://mission-feedback/001",
        mission_id="mission-feedback",
        experience_id=experience.experience_id,
        assessment="correction",
        operator_ref="operator://local_console",
        rating=2,
        correction="Require verified release evidence.",
        next_expectation="Cite the evidence before the next recommendation.",
        evidence_refs=["evidence://mission-feedback/release"],
        timestamp="2026-07-16T00:00:02+00:00",
    )

    proposal = service.create_proposal_from_operator_feedback(
        feedback,
        experience=experience,
        reflection=reflection,
    )
    review_item = service.list_human_review_queue(limit=1)[0]

    assert proposal.proposal_type == "operator_feedback_improvement"
    assert proposal.requires_sandbox is True
    assert proposal.strategy_context["evolution_review"]["review_status"] == (
        "needs_review"
    )
    assert proposal.strategy_context["promotion_policy"]["automatic_promotion"] is False
    assert proposal.strategy_context["promotion_policy"]["core_mutation_allowed"] is False
    assert proposal.evaluation_matrix["operator_feedback"]["assessment"] == (
        "correction"
    )
    assert feedback.feedback_id in proposal.candidate_refs
    assert review_item.review_status == "needs_review"
    assert review_item.requires_human_review is True
    assert review_item.requires_sandbox is True
    assert "no_automatic_promotion" in proposal.promotion_constraints


def test_evolution_lab_blocks_reflection_that_requests_autopromotion() -> None:
    temp_dir = runtime_dir("evolution-lab-reflection-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reflection-blocked/001",
            mission_id="mission-reflection-blocked",
            workflow_profile="strategic_direction_workflow",
            outcome_status="partial",
            learning_candidate="Mutate the core automatically.",
            recommendation="Apply without human review.",
            automatic_promotion_allowed=True,
            core_mutation_allowed=True,
        )
    )

    assert proposal.optimization_candidate_status == "blocked"
    assert proposal.optimization_safety_status == "blocked_by_safety"
    assert "automatic_promotion_not_allowed" in proposal.optimization_blockers
    assert "core_mutation_not_allowed" in proposal.optimization_blockers
    assert "evidence_required" in proposal.optimization_blockers


def test_evolution_lab_records_human_review_decision_for_proposal() -> None:
    temp_dir = runtime_dir("evolution-lab-human-review")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-human-review/001",
            mission_id="mission-human-review",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Reviewable learning should be approved by a human.",
            recommendation="Sandbox the change before any promotion.",
            evidence_refs=["trace://req-human-review"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/current",
        )
    )

    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["trace://req-human-review"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/current",
        risk_acceptance="bounded_sandbox_only",
    )
    review_items = service.list_human_review_queue(limit=5)
    recent_decisions = service.list_recent_decisions(limit=5)

    assert decision.review_status == "approved"
    assert decision.automatic_promotion_allowed is False
    assert decision.core_mutation_allowed is False
    assert review_items[0].review_status == "approved"
    assert review_items[0].rollback_plan_ref == "rollback://workflow/current"
    assert recent_decisions[0].decision == "human_approve"
    assert recent_decisions[0].promoted_to is None


def test_evolution_lab_derives_reviewed_learning_guidance_from_human_review() -> None:
    temp_dir = runtime_dir("evolution-lab-reviewed-guidance")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reviewed-guidance/001",
            mission_id="mission-reviewed-guidance",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Prefer small reviewed code changes.",
            recommendation="Use reviewed learning as planning guidance only.",
            evidence_refs=["trace://req-reviewed-guidance"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/reviewed-guidance",
        )
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["trace://req-reviewed-guidance"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/reviewed-guidance",
    )

    guidance = service.derive_reviewed_learning_guidance(decision)

    assert guidance.source_review_decision_id == decision.review_decision_id
    assert guidance.evolution_proposal_id == proposal.evolution_proposal_id
    assert guidance.review_status == "sandboxed"
    assert guidance.workflow_profile == "software_change_workflow"
    assert guidance.route == "software_change_workflow"
    assert guidance.domain == "software_change_workflow"
    assert guidance.guidance_summary == "Use reviewed learning as planning guidance only."
    assert guidance.allowed_usage == [
        "sandbox_planning_context",
        "sandbox_synthesis_context",
        "evaluation_context",
    ]
    assert "trace://req-reviewed-guidance" in guidance.evidence_refs
    assert "baseline://sovereign-core/current" in guidance.evidence_refs
    assert guidance.rollback_plan_ref == "rollback://workflow/reviewed-guidance"
    assert guidance.automatic_promotion_allowed is False
    assert guidance.core_mutation_allowed is False


def test_evolution_lab_builds_sandbox_to_release_checklist() -> None:
    temp_dir = runtime_dir("evolution-lab-release-checklist")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-release-checklist/001",
            mission_id="mission-release-checklist",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Use reviewed release checklist.",
            recommendation="Promote only after release gate.",
            evidence_refs=["trace://req-release-checklist"],
            proposed_tests=["python tools/engineering_gate.py --mode standard"],
            rollback_plan_ref="rollback://workflow/release-checklist",
        )
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["trace://req-release-checklist"],
        proposed_tests=["python tools/engineering_gate.py --mode standard"],
        rollback_plan_ref="rollback://workflow/release-checklist",
    )

    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=decision,
    )

    assert checklist.checklist_status == "ready_for_release_review"
    assert checklist.human_review_status == "sandboxed"
    assert "human_review" in checklist.required_gates
    assert "standard_engineering_gate" in checklist.required_gates
    assert checklist.evidence_refs == ["trace://req-release-checklist"]
    assert checklist.proposed_tests == [
        "python tools/engineering_gate.py --mode standard"
    ]
    assert checklist.rollback_plan_ref == "rollback://workflow/release-checklist"
    assert checklist.blockers == []
    assert checklist.automatic_promotion_allowed is False
    assert checklist.core_mutation_allowed is False


def test_evolution_lab_blocks_release_checklist_with_foreign_review() -> None:
    temp_dir = runtime_dir("evolution-lab-foreign-release-review")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    first = service.create_proposal(
        proposal_type="review_integrity",
        target_scope="workflow:first",
        hypothesis="First bounded release candidate.",
        expected_gain="Validated release path.",
        baseline_refs=["baseline://release/first"],
        proposed_tests=["test:first"],
    )
    second = service.create_proposal(
        proposal_type="review_integrity",
        target_scope="workflow:second",
        hypothesis="Second bounded release candidate.",
        expected_gain="Validated release path.",
        baseline_refs=["baseline://release/second"],
        proposed_tests=["test:second"],
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(first.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://release/first"],
        proposed_tests=["test:first"],
        rollback_plan_ref="rollback://release/first",
    )

    with pytest.raises(
        ValueError,
        match="review decision does not belong to the evolution proposal",
    ):
        service.build_sandbox_to_release_checklist(
            second,
            review_decision=decision,
        )


def test_evolution_lab_passes_complete_promotion_gate_without_authorizing_it() -> None:
    checklist = SandboxToReleaseChecklistContract(
        checklist_id="sandbox-release-checklist://proposal-pass",
        evolution_proposal_id="proposal-pass",
        release_scope="workflow:software_change_workflow",
        checklist_status="ready_for_release_review",
        human_review_status="approved",
        required_gates=[
            "human_review",
            "evidence",
            "proposed_tests",
            "rollback_plan",
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
        evidence_refs=["evidence://proposal-pass"],
        proposed_tests=["pytest tests/unit/test_release.py"],
        rollback_plan_ref="rollback://proposal-pass",
    )

    decision = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    payload = EvolutionLabService.promotion_gate_event_payload(decision)

    assert decision.gate_status == "passed"
    assert decision.decision == "eligible_for_human_promotion_decision"
    assert decision.release_conclusion == (
        "release_gate_passed_pending_human_decision"
    )
    assert decision.missing_gates == []
    assert decision.blockers == []
    assert decision.promotion_eligible is True
    assert decision.promotion_authorized is False
    assert payload["promotion_gate_status"] == "passed"
    assert payload["promotion_gate_evidence_refs"] == ["evidence://proposal-pass"]
    assert payload["automatic_promotion_allowed"] is False


def test_evolution_lab_blocks_spoofed_or_incomplete_promotion_gate() -> None:
    checklist = SandboxToReleaseChecklistContract(
        checklist_id="sandbox-release-checklist://proposal-blocked",
        evolution_proposal_id="proposal-blocked",
        release_scope="workflow:software_change_workflow",
        checklist_status="blocked",
        human_review_status="needs_review",
        required_gates=[],
    )

    decision = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "human_review",
            "evidence",
            "proposed_tests",
            "rollback_plan",
            "standard_engineering_gate",
        ],
    )

    assert decision.gate_status == "blocked"
    assert decision.decision == "promotion_blocked"
    assert decision.release_conclusion == "promotion_blocked_by_release_gate"
    assert "human_review" in decision.missing_gates
    assert "evidence" in decision.missing_gates
    assert "proposed_tests" in decision.missing_gates
    assert "rollback_plan" in decision.missing_gates
    assert "release_gate_before_promotion" in decision.missing_gates
    assert "checklist_not_ready_for_release_review" in decision.blockers
    assert decision.promotion_eligible is False
    assert decision.promotion_authorized is False


def test_evolution_lab_creates_sandbox_proposal_from_procedural_playbook_candidate() -> None:
    temp_dir = runtime_dir("evolution-lab-procedural-playbook")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_procedural_playbook_candidate(
        ProceduralPlaybookCandidateContract(
            playbook_candidate_id="playbook-candidate://software-change/001",
            procedure_name="bounded patch review",
            workflow_profile="software_change_workflow",
            route="software_engineering",
            domain="engenharia_de_software",
            bounded_steps=[
                "collect evidence",
                "run targeted tests",
                "prepare rollback",
            ],
            evidence_refs=["trace://req-playbook"],
            source_artifact_refs=["artifact://procedural/software/v1"],
            source_reflection_refs=["reflection://mission/001"],
            proposed_tests=["pytest services/memory-service/tests"],
            rollback_plan_ref="rollback://playbook/001",
            timestamp="2026-07-04T00:00:00Z",
        )
    )

    assert proposal.proposal_type == "procedural_playbook_candidate"
    assert proposal.optimization_candidate_status == "candidate"
    assert proposal.optimization_safety_status == "sandbox_only"
    assert proposal.evaluation_matrix["procedural_playbook_candidate"][
        "manual_review_required"
    ] is True
    assert (
        proposal.strategy_context["promotion_policy"]["manual_review_required"]
        is True
    )
    assert (
        proposal.strategy_context["promotion_policy"]["automatic_promotion"]
        is False
    )
    assert (
        proposal.strategy_context["promotion_policy"]["release_gate_required"]
        is True
    )
    assert "playbook://promotion/manual_review_required" in proposal.source_signals


def test_evolution_lab_derives_reviewed_playbook_from_persisted_human_approval() -> None:
    temp_dir = runtime_dir("evolution-lab-reviewed-procedural-playbook")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = _procedural_playbook_candidate()
    proposal = service.create_proposal_from_procedural_playbook_candidate(candidate)
    with pytest.raises(ValueError, match="bounded operator_ref"):
        service.review_proposal(
            evolution_proposal_id=str(proposal.evolution_proposal_id),
            action="approve",
            operator_ref="  ",
            evidence_refs=["evidence://playbook/human-review"],
            proposed_tests=list(candidate.proposed_tests),
            rollback_plan_ref=candidate.rollback_plan_ref,
            release_version="1.2.0",
        )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://playbook/human-review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
        release_version="1.2.0",
    )
    checklist, gate = _playbook_release_gate(service, proposal, decision)

    playbook = service.derive_reviewed_procedural_playbook(
        candidate,
        decision,
        version="1.2.0",
        release_checklist=checklist,
        promotion_gate=gate,
    )

    assert decision.review_status == "approved"
    assert playbook.playbook_id.startswith("reviewed-playbook://")
    assert playbook.version == "1.2.0"
    assert playbook.source_candidate_id == candidate.playbook_candidate_id
    assert playbook.source_review_decision_id == decision.review_decision_id
    assert playbook.evolution_proposal_id == proposal.evolution_proposal_id
    assert playbook.review_status == "approved"
    assert playbook.bounded_steps == candidate.bounded_steps
    assert playbook.allowed_usage == ["planning_context"]
    assert candidate.evidence_refs[0] in playbook.evidence_refs
    assert "evidence://playbook/human-review" in playbook.evidence_refs
    assert decision.review_decision_id in playbook.evidence_refs
    assert playbook.rollback_plan_ref == candidate.rollback_plan_ref
    assert playbook.read_only is True
    assert playbook.execution_allowed is False
    assert playbook.tool_dispatch_allowed is False
    assert playbook.memory_write_mode == "read_only"
    assert playbook.automatic_promotion_allowed is False
    assert playbook.core_mutation_allowed is False
    assert checklist.checklist_status == "ready_for_release_review"
    assert checklist.candidate_type == "procedural_playbook_candidate"
    assert checklist.candidate_version == "1.2.0"
    assert gate.gate_status == "passed"
    assert checklist.checklist_id in playbook.evidence_refs
    assert gate.promotion_gate_id in playbook.evidence_refs
    assert service.verify_persisted_reviewed_procedural_playbook(playbook) is True
    assert (
        service.verify_persisted_reviewed_procedural_playbook(
            replace(playbook, bounded_steps=["spoofed runtime guidance"])
        )
        is False
    )
    assert (
        service.verify_persisted_reviewed_procedural_playbook(
            replace(playbook, timestamp="9999-12-31T23:59:59+00:00")
        )
        is False
    )
    revocation_ref = "human-review://playbook/revoke-1.2.0"
    revoked_playbook = replace(
        playbook,
        review_status="revoked",
        evidence_refs=[revocation_ref, *playbook.evidence_refs][:20],
        revoked_at="2026-07-19T00:00:00Z",
        revocation_ref=revocation_ref,
    )
    assert (
        service.verify_persisted_reviewed_procedural_playbook(revoked_playbook)
        is True
    )

    forged_checklist = replace(
        checklist,
        release_scope="",
        evidence_refs=[],
        proposed_tests=[],
        rollback_plan_ref=None,
        required_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    forged_gate = replace(
        gate,
        checklist_id=forged_checklist.checklist_id,
        release_scope="",
        required_gates=list(forged_checklist.required_gates),
        completed_gates=list(forged_checklist.required_gates),
        evidence_refs=[],
    )
    with pytest.raises(ValueError, match="canonical_playbook"):
        service.derive_reviewed_procedural_playbook(
            candidate,
            decision,
            version="1.2.0",
            release_checklist=forged_checklist,
            promotion_gate=forged_gate,
        )

    with pytest.raises(ValueError, match="new human review"):
        service.derive_reviewed_procedural_playbook(
            candidate,
            decision,
            version="2.0.0",
            release_checklist=checklist,
            promotion_gate=gate,
        )


def test_evolution_lab_requires_human_approved_semver_before_playbook_release() -> None:
    temp_dir = runtime_dir("evolution-lab-playbook-version-review")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = _procedural_playbook_candidate("version-review")
    proposal = service.create_proposal_from_procedural_playbook_candidate(candidate)
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://playbook/version-review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    checklist, gate = _playbook_release_gate(service, proposal, decision)

    assert decision.review_status == "needs_review"
    assert decision.candidate_version is None
    assert "playbook_release_version_required" in decision.review_notes
    assert checklist.checklist_status == "blocked"
    assert gate.gate_status == "blocked"
    with pytest.raises(ValueError, match="new human review"):
        service.derive_reviewed_procedural_playbook(
            candidate,
            decision,
            version="1.0.0",
            release_checklist=checklist,
            promotion_gate=gate,
        )


@pytest.mark.parametrize(
    ("case_id", "release_version"),
    [
        ("leading-major-zero", "01.0.0"),
        ("leading-minor-zero", "1.01.0"),
        ("leading-patch-zero", "1.0.01"),
        ("arabic-indic-digit", "١.2.3"),
        ("fullwidth-digit", "１.2.3"),
    ],
)
def test_evolution_review_rejects_noncanonical_playbook_release_semver(
    case_id: str,
    release_version: str,
) -> None:
    temp_dir = runtime_dir(f"evolution-playbook-semver-{case_id}")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = _procedural_playbook_candidate(case_id)
    proposal = service.create_proposal_from_procedural_playbook_candidate(candidate)

    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=[f"evidence://playbook/{case_id}"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
        release_version=release_version,
    )

    assert decision.review_status == "needs_review"
    assert decision.candidate_version is None
    assert "playbook_release_version_required" in decision.review_notes


def test_evolution_lab_rejects_playbook_review_rollback_override() -> None:
    temp_dir = runtime_dir("evolution-lab-playbook-rollback-override")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = _procedural_playbook_candidate("rollback-override")
    proposal = service.create_proposal_from_procedural_playbook_candidate(candidate)
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://playbook/rollback-override"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref="rollback://playbook/forged-override",
        release_version="1.0.0",
    )
    checklist, gate = _playbook_release_gate(service, proposal, decision)

    with pytest.raises(ValueError, match="persisted review"):
        service.derive_reviewed_procedural_playbook(
            candidate,
            decision,
            version="1.0.0",
            release_checklist=checklist,
            promotion_gate=gate,
        )


def test_evolution_lab_rejects_spoofed_review_or_changed_playbook_candidate() -> None:
    temp_dir = runtime_dir("evolution-lab-spoofed-procedural-playbook")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = _procedural_playbook_candidate("spoof-check")
    proposal = service.create_proposal_from_procedural_playbook_candidate(candidate)
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://playbook/spoof-check"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
        release_version="1.0.0",
    )
    checklist, gate = _playbook_release_gate(service, proposal, decision)

    with pytest.raises(ValueError, match="persisted review"):
        service.derive_reviewed_procedural_playbook(
            candidate,
            replace(
                decision,
                review_decision_id="review-decision://forged/001",
            ),
            version="1.0.0",
            release_checklist=checklist,
            promotion_gate=gate,
        )

    with pytest.raises(ValueError, match="persisted review"):
        service.derive_reviewed_procedural_playbook(
            replace(candidate, bounded_steps=["dispatch a tool automatically"]),
            decision,
            version="1.0.0",
            release_checklist=checklist,
            promotion_gate=gate,
        )

    for invalid_version in ("v1", "01.0.0", "1.01.0", "1.0.01", "١.2.3"):
        with pytest.raises(ValueError, match="semver"):
            service.derive_reviewed_procedural_playbook(
                candidate,
                decision,
                version=invalid_version,
                release_checklist=checklist,
                promotion_gate=gate,
            )


@pytest.mark.parametrize(
    ("candidate_changes", "review_evidence", "review_tests", "review_rollback"),
    [
        (
            {"evidence_refs": []},
            ["evidence://playbook/review"],
            ["pytest tests/unit/test_memory_influence_policy.py"],
            "rollback://playbook/incomplete",
        ),
        (
            {},
            [],
            ["pytest tests/unit/test_memory_influence_policy.py"],
            "rollback://playbook/incomplete",
        ),
        (
            {"proposed_tests": []},
            ["evidence://playbook/review"],
            [],
            "rollback://playbook/incomplete",
        ),
        (
            {"rollback_plan_ref": None},
            ["evidence://playbook/review"],
            ["pytest tests/unit/test_memory_influence_policy.py"],
            None,
        ),
    ],
    ids=(
        "candidate-evidence",
        "review-evidence",
        "review-tests",
        "rollback",
    ),
)
def test_evolution_lab_rejects_incomplete_reviewed_playbook_derivation(
    candidate_changes: dict[str, object],
    review_evidence: list[str],
    review_tests: list[str],
    review_rollback: str | None,
) -> None:
    temp_dir = runtime_dir("evolution-lab-incomplete-procedural-playbook")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = replace(
        _procedural_playbook_candidate("incomplete"),
        **candidate_changes,
    )
    proposal = service.create_proposal_from_procedural_playbook_candidate(candidate)
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
        evidence_refs=review_evidence,
        proposed_tests=review_tests,
        rollback_plan_ref=review_rollback,
        release_version="1.0.0",
    )
    checklist, gate = _playbook_release_gate(service, proposal, decision)

    with pytest.raises(ValueError):
        service.derive_reviewed_procedural_playbook(
            candidate,
            decision,
            version="1.0.0",
            release_checklist=checklist,
            promotion_gate=gate,
        )


def test_skill_miner_creates_and_registers_only_inactive_candidate_end_to_end() -> None:
    temp_dir = runtime_dir("evolution-lab-skill-miner")
    memory = MemoryService(
        database_url=f"sqlite:///{(temp_dir / 'memory.db').as_posix()}"
    )
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://release-evidence",
        pattern_type="repeated_successful_workflow",
        pattern_status="evidence_ready_for_human_review",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        occurrence_count=2,
        minimum_occurrences=2,
        successful_occurrences=2,
        non_successful_occurrences=0,
        confidence_status="bounded_moderate",
        outcome_summary="completed=2",
        pattern_summary="two compatible completed experiences",
        experience_refs=["experience://release/1", "experience://release/2"],
        reflection_refs=["reflection://release/1", "reflection://release/2"],
        feedback_refs=["operator-feedback://release/1"],
        evidence_refs=["trace://release/1", "trace://release/2"],
        recurring_signals=["verify_release_evidence", "report_missing_gates"],
        conflict_flags=[],
        blockers=[],
        generated_at="2026-07-16T14:00:00Z",
    )
    request = SkillMiningRequestContract(
        mining_request_id="skill-mining-request://release-evidence/1",
        source_pattern_ref=pattern.pattern_id,
        skill_id="skill://release-evidence",
        skill_name="release evidence verification",
        version="1.0.0",
        specialist_type="software_change_specialist",
        inputs=["change_scope", "release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=list(pattern.recurring_signals),
        risk_level=RiskLevel.MODERATE,
        failure_modes=["missing_release_evidence"],
        proposed_tests=["run release evidence tests"],
        rollback_plan_ref="rollback://skill/release-evidence/1.0.0",
        timestamp="2026-07-16T15:00:00Z",
    )

    result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=request,
    )
    assert result.candidate is not None
    stored = memory.record_skill_candidate(result.candidate)
    repeated_request = SkillMiningRequestContract(
        **{
            **request.__dict__,
            "mining_request_id": "skill-mining-request://release-evidence/2",
            "timestamp": "2026-07-16T15:05:00Z",
        }
    )
    repeated_result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=repeated_request,
    )
    assert repeated_result.candidate is not None
    repeated_stored = memory.record_skill_candidate(repeated_result.candidate)

    assert result.mining_status == "candidate_created_inactive"
    assert result.eligibility_status == "eligible"
    assert result.blockers == []
    assert result.source_authority_status == (
        "observation_only_requires_miner_and_review"
    )
    assert repeated_stored == stored
    assert repeated_result.candidate.skill_candidate_id == (
        stored.candidate.skill_candidate_id
    )
    assert stored.candidate.registry_status == "candidate_inactive"
    assert stored.candidate.review_status == "needs_review"
    assert stored.candidate.activation_status == "inactive"
    assert stored.candidate.source_pattern_refs == [pattern.pattern_id]
    assert stored.candidate.automatic_activation_allowed is False
    assert stored.candidate.automatic_promotion_allowed is False
    assert stored.candidate.core_mutation_allowed is False


def test_skill_miner_returns_no_candidate_for_insufficient_pattern() -> None:
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://insufficient",
        pattern_type="repeated_successful_workflow",
        pattern_status="attention_required",
        workflow_profile="software_change_workflow",
        route="software_development",
        domain="software_engineering",
        occurrence_count=1,
        minimum_occurrences=2,
        successful_occurrences=1,
        non_successful_occurrences=0,
        confidence_status="insufficient",
        outcome_summary="completed=1",
        pattern_summary="single experience",
        experience_refs=["experience://insufficient/1"],
        reflection_refs=["reflection://insufficient/1"],
        feedback_refs=[],
        evidence_refs=["trace://insufficient/1"],
        recurring_signals=["verify_release_evidence"],
        conflict_flags=[],
        blockers=["recurrence_threshold_not_met"],
        generated_at="2026-07-16T14:00:00Z",
    )
    request = SkillMiningRequestContract(
        mining_request_id="skill-mining-request://insufficient/1",
        source_pattern_ref=pattern.pattern_id,
        skill_id="skill://insufficient",
        skill_name="insufficient skill",
        version="1.0.0",
        specialist_type="software_change_specialist",
        inputs=["input"],
        outputs=["output"],
        allowed_tools=[],
        bounded_instructions=["bounded step"],
        risk_level=RiskLevel.LOW,
        failure_modes=["invalid_output"],
        proposed_tests=["run candidate test"],
        rollback_plan_ref="rollback://skill/insufficient/1.0.0",
        timestamp="2026-07-16T15:00:00Z",
    )

    result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=request,
    )

    assert result.mining_status == "blocked"
    assert result.candidate is None
    assert "recurrence_threshold_not_met" in result.blockers
    assert "pattern_not_eligible_for_skill_mining" in result.blockers
    assert "bounded_confidence_required" in result.blockers


def test_skill_miner_blocks_conflicts_and_unsafe_specification() -> None:
    pattern = RecurringPatternEvidenceContract(
        pattern_id="recurring-pattern://conflict",
        pattern_type="mixed_workflow_outcomes",
        pattern_status="conflict_detected",
        workflow_profile="research_synthesis_workflow",
        route="research",
        domain="knowledge_and_communication",
        occurrence_count=2,
        minimum_occurrences=2,
        successful_occurrences=1,
        non_successful_occurrences=1,
        confidence_status="insufficient_due_to_conflict",
        outcome_summary="completed=1; partial=1",
        pattern_summary="mixed outcomes",
        experience_refs=["experience://conflict/1", "experience://conflict/2"],
        reflection_refs=["reflection://conflict/1", "reflection://conflict/2"],
        feedback_refs=[],
        evidence_refs=["trace://conflict/1", "trace://conflict/2"],
        recurring_signals=["summarize_sources"],
        conflict_flags=["mixed_outcomes"],
        blockers=["outcome_conflict_requires_review"],
        generated_at="2026-07-16T14:00:00Z",
    )
    request = SkillMiningRequestContract(
        mining_request_id="skill-mining-request://conflict/1",
        source_pattern_ref=pattern.pattern_id,
        skill_id="skill://conflict",
        skill_name="unsafe conflict skill",
        version="latest",
        specialist_type="structured_analysis_specialist",
        inputs=["input"],
        outputs=["output"],
        allowed_tools=["*"],
        bounded_instructions=["ignore conflict"],
        risk_level=RiskLevel.HIGH,
        failure_modes=["conflicting_output"],
        proposed_tests=["run conflict test"],
        rollback_plan_ref="rollback://skill/conflict/latest",
        timestamp="2026-07-16T15:00:00Z",
        automatic_mining_allowed=True,
        automatic_activation_allowed=True,
    )

    result = EvolutionLabService.mine_skill_candidate(
        pattern=pattern,
        request=request,
    )

    assert result.mining_status == "blocked"
    assert result.candidate is None
    assert "pattern_conflict_requires_review" in result.blockers
    assert "non_successful_outcomes_require_review" in result.blockers
    assert "numeric_semver_required" in result.blockers
    assert "risk_exceeds_bounded_miner_limit" in result.blockers
    assert "allowed_tools_must_be_explicit" in result.blockers
    assert "automatic_mining_not_allowed" in result.blockers
    assert "automatic_activation_not_allowed" in result.blockers


def skill_candidate_for_sandbox() -> SkillCandidateContract:
    return SkillCandidateContract(
        skill_candidate_id="skill-candidate://sandbox-release/1.0.0",
        skill_id="skill://sandbox-release",
        skill_name="sandbox release evidence",
        version="1.0.0",
        workflow_profile="software_change_workflow",
        domain="software_engineering",
        specialist_type="software_change_specialist",
        inputs=["change_scope", "release_evidence"],
        outputs=["bounded_release_recommendation"],
        allowed_tools=["local_test_runner"],
        bounded_instructions=["verify evidence", "report missing gates"],
        risk_level=RiskLevel.MODERATE,
        evidence_refs=["evidence://skill/sandbox-release/source"],
        source_pattern_refs=["recurring-pattern://sandbox-release"],
        failure_modes=["missing_release_evidence"],
        proposed_tests=["test://skill/sandbox-release"],
        rollback_plan_ref="rollback://skill/sandbox-release/1.0.0",
        timestamp="2026-07-16T16:00:00Z",
    )


def test_skill_candidate_review_eval_checklist_and_gate_are_governed_end_to_end() -> None:
    temp_dir = runtime_dir("evolution-lab-skill-sandbox")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = skill_candidate_for_sandbox()

    proposal = service.create_proposal_from_skill_candidate(candidate)
    queue_item = service.list_human_review_queue(limit=1)[0]
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://skill/sandbox-release/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    evaluation = service.evaluate_skill_candidate_in_sandbox(
        candidate=candidate,
        proposal=proposal,
        review_decision=review,
        test_cases={
            "expected-output": {
                "output_contract_satisfied": True,
                "failure_mode_contained": True,
            },
            "tool-boundary": {
                "allowed_tool_only": True,
                "core_unchanged": True,
            },
        },
        evidence_refs=["eval://skill/sandbox-release/run-1"],
        generated_at="2026-07-16T16:05:00Z",
    )
    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        skill_sandbox_eval=evaluation,
    )
    gate = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )
    reviewed_queue_item = service.list_human_review_queue(limit=1)[0]

    assert proposal.proposal_type == "skill_candidate"
    assert proposal.optimization_candidate_status == "candidate"
    assert proposal.optimization_safety_status == "sandbox_only"
    assert candidate.skill_candidate_id in proposal.candidate_refs
    assert queue_item.candidate_refs == proposal.candidate_refs
    assert review.review_status == "sandboxed"
    assert reviewed_queue_item.review_status == "sandboxed"
    assert review.candidate_identity_ref == candidate.skill_id
    assert review.candidate_version == candidate.version
    assert evaluation.eval_status == "passed_pending_release_gate"
    assert evaluation.pass_rate == 1.0
    assert evaluation.failed_cases == 0
    assert evaluation.runtime_activation_allowed is False
    assert evaluation.promotion_authorized is False
    assert checklist.checklist_status == "ready_for_release_review"
    assert checklist.candidate_type == "skill_candidate"
    assert checklist.candidate_identity_ref == candidate.skill_id
    assert checklist.candidate_version == candidate.version
    assert checklist.sandbox_eval_ref == evaluation.eval_id
    assert checklist.sandbox_eval_status == "passed_pending_release_gate"
    assert "skill_sandbox_eval" in checklist.required_gates
    assert gate.gate_status == "passed"
    assert "skill_sandbox_eval" in gate.completed_gates
    assert gate.release_conclusion == "release_gate_passed_pending_human_decision"
    assert gate.human_decision_required is True
    assert gate.promotion_authorized is False
    assert gate.automatic_promotion_allowed is False
    assert candidate.activation_status == "inactive"


def test_skill_sandbox_failure_blocks_checklist_and_promotion_gate() -> None:
    temp_dir = runtime_dir("evolution-lab-skill-sandbox-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    candidate = skill_candidate_for_sandbox()
    proposal = service.create_proposal_from_skill_candidate(candidate)
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://local_console",
        evidence_refs=["evidence://skill/sandbox-release/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )

    evaluation = service.evaluate_skill_candidate_in_sandbox(
        candidate=candidate,
        proposal=proposal,
        review_decision=review,
        test_cases={
            "tool-boundary": {
                "allowed_tool_only": False,
                "core_unchanged": True,
            }
        },
        evidence_refs=["eval://skill/sandbox-release/failed"],
        generated_at="2026-07-16T16:06:00Z",
    )
    checklist_without_eval = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
    )
    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        skill_sandbox_eval=evaluation,
    )
    gate = EvolutionLabService.evaluate_promotion_gate(
        checklist,
        completed_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
    )

    assert evaluation.eval_status == "blocked"
    assert evaluation.pass_rate == 0.0
    assert evaluation.case_results[0].failed_checks == ["allowed_tool_only"]
    assert "sandbox_pass_rate_below_threshold" in evaluation.blockers
    assert checklist_without_eval.checklist_status == "blocked"
    assert "skill_sandbox_eval_required" in checklist_without_eval.blockers
    assert checklist.checklist_status == "blocked"
    assert "skill_sandbox_eval_not_passed" in checklist.blockers
    assert gate.gate_status == "blocked"
    assert gate.promotion_authorized is False
    assert candidate.activation_status == "inactive"


def test_evolution_lab_blocks_human_approval_without_required_evidence() -> None:
    temp_dir = runtime_dir("evolution-lab-human-review-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-human-review-blocked/001",
            mission_id="mission-human-review-blocked",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Unsafe approval without evidence.",
            recommendation="Should remain in review.",
        )
    )

    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="approve",
        operator_ref="operator://local_console",
    )
    review_items = service.list_human_review_queue(limit=5)

    assert decision.review_status == "needs_review"
    assert "evidence_required_for_human_approval" in decision.review_notes
    assert "tests_required_for_human_approval" in decision.review_notes
    assert "rollback_required_for_human_approval" in decision.review_notes
    assert review_items[0].review_status == "needs_review"
    assert set(review_items[0].blockers) == {
        "evidence_required_for_human_approval",
        "tests_required_for_human_approval",
        "rollback_required_for_human_approval",
    }


def test_evolution_lab_blocks_guidance_from_unapproved_review() -> None:
    temp_dir = runtime_dir("evolution-lab-reviewed-guidance-blocked")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal_from_post_task_reflection(
        PostTaskReflectionInput(
            experience_id="experience://mission-reviewed-guidance-blocked/001",
            mission_id="mission-reviewed-guidance-blocked",
            workflow_profile="software_change_workflow",
            outcome_status="completed",
            learning_candidate="Insufficient review should not influence runtime.",
            recommendation="Keep this learning out of planning.",
        )
    )
    decision = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="needs-review",
        operator_ref="operator://local_console",
    )

    try:
        service.derive_reviewed_learning_guidance(decision)
    except ValueError as exc:
        assert "approved or sandboxed" in str(exc)
    else:
        raise AssertionError("unapproved review must not produce guidance")


def test_evolution_lab_creates_proposal_from_flow_evaluation() -> None:
    temp_dir = runtime_dir("evolution-lab-flow-proposal")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))

    proposal = service.create_proposal_from_flow_evaluation(
        FlowEvaluationInput(
            request_id="req-flow",
            session_id="sess-flow",
            mission_id="mission-flow",
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=8,
            duration_seconds=2.4,
            missing_required_events=["memory_recovered"],
            anomaly_flags=["operation_missing_completion"],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="langgraph_subflow",
            mind_alignment_status="partial",
            identity_alignment_status="healthy",
            axis_gate_status="attention_required",
            workflow_profile_status="maturation_recommended",
            workflow_output_status="partial",
            adaptive_intervention_status="healthy",
            adaptive_intervention_effectiveness="insufficient",
            adaptive_intervention_policy_status="policy_aligned",
            request_identity_status="healthy",
            mission_policy_status="attention_required",
            request_identity_mismatch_flags=["confirmation_mode_mismatch"],
            memory_causality_status="attached_only",
            workflow_checkpoint_status="attention_required",
            workflow_resume_status="manual_resume_required",
            procedural_artifact_status="candidate",
            procedural_artifact_ref_count=1,
            procedural_artifact_version=2,
            dominant_tension="equilibrar profundidade analitica com conclusao util",
            arbitration_source="mind_registry",
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            mind_domain_specialist_status="incomplete",
            mind_domain_specialist_effectiveness="incomplete",
            mind_domain_specialist_mismatch_flags=["dispatch_specialist_mismatch"],
            cognitive_recomposition_applied=True,
            cognitive_recomposition_reason=(
                "primary domain driver has no matching guided specialist route"
            ),
            cognitive_recomposition_trigger="specialist_route_impasse",
            continuity_trace_status="attention_required",
            missing_continuity_signals=["memory_continuity_mode"],
            continuity_anomaly_flags=["retomar_missing_target_mission"],
        ),
        target_scope="orchestrator-service",
    )

    assert proposal.proposal_type == "flow_evaluation_refinement"
    assert "observability://request/req-flow" in proposal.source_signals
    assert "continuity://action/retomar" in proposal.source_signals
    assert "continuity://runtime/langgraph_subflow" in proposal.source_signals
    assert "alignment://mind/partial" in proposal.source_signals
    assert "alignment://axis-gate/attention_required" in proposal.source_signals
    assert "workflow://profile-status/maturation_recommended" in proposal.source_signals
    assert "workflow://output-status/partial" in proposal.source_signals
    assert "runtime://adaptive-intervention-policy/policy_aligned" in proposal.source_signals
    assert "runtime://request-identity/healthy" in proposal.source_signals
    assert "runtime://mission-policy/attention_required" in proposal.source_signals
    assert (
        "runtime://request-identity-mismatch/confirmation_mode_mismatch"
        in proposal.source_signals
    )
    assert "memory://causality/attached_only" in proposal.source_signals
    assert "workflow://checkpoint-status/attention_required" in proposal.source_signals
    assert "artifact://procedural-status/candidate" in proposal.source_signals
    assert (
        "domain://primary-driver/dados_estatistica_e_inteligencia_analitica"
        in proposal.source_signals
    )
    assert "alignment://mind-domain-specialist/incomplete" in proposal.source_signals
    assert (
        "alignment://mind-domain-specialist-effectiveness/incomplete"
        in proposal.source_signals
    )
    assert (
        "alignment://mind-domain-specialist-mismatch/dispatch_specialist_mismatch"
        in proposal.source_signals
    )
    assert "mind://recomposition/applied" in proposal.source_signals
    assert proposal.risk_hint == "moderate"
    assert proposal.refinement_vectors[0]["axis"] in {
        "workflow_output",
        "metacognitive_guidance",
        "adaptive_intervention_policy",
        "memory_causality",
        "mind_composition",
        "mind_domain_specialist_chain",
        "mind_domain_specialist_effectiveness",
        "workflow_checkpointing",
    }
    assert "baseline_runtime" in proposal.evaluation_matrix
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["mind_composition"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["adaptive_intervention_policy"]
        == "review_recommended"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["request_identity"] == "healthy"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["mission_policy"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"][
            "mind_domain_specialist_effectiveness"
        ]
        == "incomplete"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["mind_domain_specialist_mismatch"]
        == "mismatch"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["expanded_eval"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["surface_axis"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["ecosystem_state"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["experiment_lane"]
        == "attention_required"
    )
    assert (
        proposal.evaluation_matrix["baseline_runtime"]["promotion_readiness"]
        == "blocked"
    )
    assert "wave_two_readiness_matrix" in proposal.strategy_context
    assert "controlled_wave2_experiment" in proposal.strategy_context
    assert (
        proposal.strategy_context["controlled_wave2_experiment"]["experiment_lane_status"]
        == "attention_required"
    )
    assert (
        proposal.strategy_context["wave_two_readiness_matrix"]["graphiti_zep"]["status"]
        == "stabilize_nucleus_first"
    )


def test_evolution_lab_compares_flow_evaluations() -> None:
    temp_dir = runtime_dir("evolution-lab-flow-comparison")
    service = EvolutionLabService(database_path=str(temp_dir / "evolution.db"))
    proposal = service.create_proposal(
        proposal_type="flow_evaluation_refinement",
        target_scope="orchestrator-service",
        hypothesis="Candidate path should improve trace health.",
        expected_gain="Fewer anomalies.",
        baseline_refs=["trace://req-a"],
    )

    comparison = service.compare_flow_evaluations(
        proposal,
        baseline_label="baseline",
        candidate_label="candidate",
        baseline=FlowEvaluationInput(
            request_id="req-a",
            session_id="sess-a",
            mission_id=None,
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=7,
            duration_seconds=3.2,
            missing_required_events=["memory_recovered"],
            anomaly_flags=["operation_missing_completion"],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="baseline_linear",
            mind_alignment_status="partial",
            identity_alignment_status="healthy",
            axis_gate_status="attention_required",
            workflow_profile_status="maturation_recommended",
            workflow_output_status="partial",
            adaptive_intervention_status="healthy",
            adaptive_intervention_effectiveness="insufficient",
            adaptive_intervention_policy_status="policy_aligned",
            request_identity_status="healthy",
            mission_policy_status="attention_required",
            request_identity_mismatch_flags=["confirmation_mode_mismatch"],
            memory_causality_status="attached_only",
            workflow_checkpoint_status="attention_required",
            workflow_resume_status="manual_resume_required",
            procedural_artifact_status="candidate",
            procedural_artifact_ref_count=1,
            procedural_artifact_version=2,
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            mind_domain_specialist_status="incomplete",
            mind_domain_specialist_effectiveness="insufficient",
            mind_domain_specialist_mismatch_flags=["completed_specialist_mismatch"],
            continuity_trace_status="attention_required",
            missing_continuity_signals=["memory_continuity_mode"],
            continuity_anomaly_flags=["retomar_missing_target_mission"],
        ),
        candidate=FlowEvaluationInput(
            request_id="req-b",
            session_id="sess-b",
            mission_id=None,
            governance_decision="allow_with_conditions",
            operation_status="completed",
            total_events=8,
            duration_seconds=2.1,
            missing_required_events=[],
            anomaly_flags=[],
            continuity_action="retomar",
            continuity_source="related_mission",
            continuity_runtime_mode="langgraph_subflow",
            mind_alignment_status="healthy",
            identity_alignment_status="healthy",
            axis_gate_status="healthy",
            workflow_profile_status="healthy",
            workflow_output_status="coherent",
            adaptive_intervention_status="healthy",
            adaptive_intervention_effectiveness="effective",
            adaptive_intervention_policy_status="policy_aligned",
            request_identity_status="healthy",
            mission_policy_status="policy_aligned",
            request_identity_mismatch_flags=[],
            memory_causality_status="causal_guidance",
            workflow_checkpoint_status="healthy",
            workflow_resume_status="resume_available",
            procedural_artifact_status="reusable",
            procedural_artifact_ref_count=1,
            procedural_artifact_version=3,
            primary_domain_driver="dados_estatistica_e_inteligencia_analitica",
            mind_domain_specialist_status="aligned",
            mind_domain_specialist_effectiveness="effective",
            cognitive_recomposition_applied=True,
            cognitive_recomposition_reason=(
                "primary domain driver has no matching guided specialist route"
            ),
            cognitive_recomposition_trigger="specialist_route_impasse",
            continuity_trace_status="healthy",
        ),
        governance_refs=["policy://sandbox/manual-review"],
        notes=["pilot comparison"],
    )

    assert comparison.decision.decision == "sandbox_candidate"
    assert comparison.metric_deltas["risk"] < 0
    assert comparison.metric_deltas["continuity_health"] > 0
    assert comparison.metric_deltas["runtime_statefulness"] > 0
    assert comparison.metric_deltas["axis_gate"] > 0
    assert comparison.metric_deltas["workflow_profile"] > 0
    assert comparison.metric_deltas["workflow_output"] > 0
    assert comparison.metric_deltas["adaptive_intervention_policy"] > 0
    assert comparison.metric_deltas["mission_policy"] > 0
    assert comparison.metric_deltas["memory_causality"] > 0
    assert comparison.metric_deltas["workflow_checkpoint"] > 0
    assert comparison.metric_deltas["workflow_resume"] > 0
    assert comparison.metric_deltas["procedural_artifact"] > 0
    assert comparison.metric_deltas["mind_domain_specialist"] > 0
    assert comparison.metric_deltas["mind_domain_specialist_effectiveness"] > 0
    assert comparison.metric_deltas["mind_domain_specialist_mismatch"] > 0


def _controlled_workflow_eval_artifacts(
    service: EvolutionLabService,
    *,
    suffix: str = "001",
    generated_at: str = "2026-08-11T20:00:00Z",
) -> tuple[
    WorkflowProfileVersionContract,
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
    WorkflowVariantEvalCasePackContract,
    WorkflowVariantEvalRunContract,
]:
    registry = service.build_workflow_version_registry(
        registry_version="1.0.0",
        generated_at="2026-08-11T19:00:00Z",
        evidence_refs=["evidence://workflow-eval/registry"],
    )
    baseline = next(
        version
        for version in registry.versions
        if version.workflow_profile == "software_change_workflow"
    )
    candidate_steps = [*baseline.workflow_steps, "record bounded variant evidence"]
    candidate_checkpoints = [
        *baseline.workflow_checkpoints,
        "bounded_variant_evidence_recorded",
    ]
    candidate = replace(
        baseline,
        workflow_version_id="workflow-version://software_change_workflow/1.1.0",
        version="1.1.0",
        lifecycle_status="candidate_inactive",
        definition_hash=workflow_definition_hash(
            workflow_steps=candidate_steps,
            workflow_checkpoints=candidate_checkpoints,
            workflow_decision_points=baseline.workflow_decision_points,
            success_criteria=baseline.success_criteria,
        ),
        workflow_steps=candidate_steps,
        workflow_checkpoints=candidate_checkpoints,
        evidence_refs=[
            *baseline.evidence_refs,
            "recurring-pattern://workflow-eval/software-change",
            "review-decision://workflow-eval/software-change/001",
        ],
        proposed_tests=["test://workflow-eval/software-change"],
        rollback_plan_ref="rollback://workflow-eval/software-change/1.0.0",
        baseline_version_ref=baseline.workflow_version_id,
        change_summary="record bounded variant evidence",
        risk_level="moderate",
        review_status="needs_review",
        runtime_binding_status="inactive_candidate",
        human_review_required=True,
        sandbox_required=True,
    )
    registry = service.register_workflow_candidate_version(registry, candidate)
    input_fingerprint = "a" * 64
    control = WorkflowVariantEvalControlSnapshotContract(
        control_snapshot_id=f"workflow-eval-control://software-change/{suffix}",
        workflow_policy_ref="workflow-policy://software-change/1.0.0/control",
        workflow_policy_version="1.0.0",
        workflow_policy_source_registry_ref=baseline.source_registry_ref,
        workflow_policy_source_registry_fingerprint=(
            baseline.source_registry_fingerprint
        ),
        governance_policy_ref="governance-policy://workflow-eval/controlled",
        governance_policy_version="1.0.0",
        input_fingerprint=input_fingerprint,
        memory_policy_refs=["memory-policy://workflow-eval/controlled"],
        memory_policy_version_refs={
            "memory-policy://workflow-eval/controlled": "1.0.0"
        },
        memory_input_fingerprint="b" * 64,
        evaluator_version="1.0.0",
        deterministic_seed=42,
        fixed_clock="2026-08-11T19:30:00Z",
    )
    control_fingerprint = workflow_variant_eval_control_fingerprint(control)
    common_observation = {
        "case_id": "software-change-controlled-case",
        "case_version": "1.0.0",
        "input_snapshot_fingerprint": input_fingerprint,
        "control_snapshot_id": control.control_snapshot_id,
        "control_snapshot_fingerprint": control_fingerprint,
        "action_count": 4,
        "memory_participating_refs": ["memory://workflow-eval/signal-001"],
        "evidence_refs": [
            "evidence://workflow-eval/input",
            "evidence://workflow-eval/outcome",
        ],
        "limitations": [],
        "observed_at": control.fixed_clock,
    }
    baseline_observation = WorkflowVariantEvalObservationContract(
        **common_observation,
        observation_id=f"workflow-eval-observation://baseline/{suffix}",
        arm="baseline",
        workflow_version_ref=baseline.workflow_version_id,
        definition_hash=baseline.definition_hash,
        outcome_ref=f"outcome://workflow-eval/baseline/{suffix}",
        outcome_status="failed",
        contract_checks={"bounded": True, "completed": False},
        rework_count=2,
        expected_workflow_steps=list(baseline.workflow_steps),
        expected_checkpoint_refs=list(baseline.workflow_checkpoints),
        expected_decision_points=list(baseline.workflow_decision_points),
        expected_success_criteria=list(baseline.success_criteria),
        observed_checkpoint_refs=[],
        memory_declared_causal_refs=[],
    )
    candidate_observation = WorkflowVariantEvalObservationContract(
        **common_observation,
        observation_id=f"workflow-eval-observation://candidate/{suffix}",
        arm="candidate",
        workflow_version_ref=candidate.workflow_version_id,
        definition_hash=candidate.definition_hash,
        outcome_ref=f"outcome://workflow-eval/candidate/{suffix}",
        outcome_status="completed",
        contract_checks={"bounded": True, "completed": True},
        rework_count=0,
        expected_workflow_steps=list(candidate.workflow_steps),
        expected_checkpoint_refs=list(candidate.workflow_checkpoints),
        expected_decision_points=list(candidate.workflow_decision_points),
        expected_success_criteria=list(candidate.success_criteria),
        observed_checkpoint_refs=list(candidate.workflow_checkpoints),
        memory_declared_causal_refs=["memory://workflow-eval/signal-001"],
    )
    case_pack_id = f"workflow-eval-case-pack://software-change/{suffix}"
    case = WorkflowVariantEvalCaseContract(
        case_pack_id=case_pack_id,
        case_pack_version="1.0.0",
        case_id="software-change-controlled-case",
        case_version="1.0.0",
        scenario_ref=f"scenario://workflow-eval/software-change/{suffix}",
        input_snapshot_fingerprint=input_fingerprint,
        workflow_profile=baseline.workflow_profile,
        route=baseline.route,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        required_candidate_steps=["record bounded variant evidence"],
        required_candidate_checkpoints=["bounded_variant_evidence_recorded"],
        required_candidate_decision_points=[],
        required_candidate_success_criteria=[],
        contract_check_refs=["bounded", "completed"],
        control_snapshot=control,
        baseline_observation=baseline_observation,
        candidate_observation=candidate_observation,
        evidence_refs=[
            "evidence://workflow-eval/case-definition",
            "evidence://workflow-eval/paired-observations",
        ],
    )
    pack = WorkflowVariantEvalCasePackContract(
        case_pack_id=case_pack_id,
        case_pack_version="1.0.0",
        workflow_profile=baseline.workflow_profile,
        route=baseline.route,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        scope_refs=["scope://workflow-eval/software-change"],
        cases=[case],
        evidence_refs=[
            "evidence://workflow-eval/pack",
            "evidence://workflow-eval/policy-control",
        ],
        generated_at=generated_at,
    )
    pack_fingerprint = workflow_variant_eval_case_pack_fingerprint(pack)
    result = service.evaluate_workflow_variant_case(
        baseline=baseline,
        candidate=candidate,
        case=case,
        case_pack_fingerprint=pack_fingerprint,
    )
    run = WorkflowVariantEvalRunContract(
        run_id=f"workflow-variant-eval://software-change/{suffix}",
        case_pack_id=pack.case_pack_id,
        case_pack_version=pack.case_pack_version,
        case_pack_fingerprint=pack_fingerprint,
        workflow_profile=pack.workflow_profile,
        route=pack.route,
        baseline_version_ref=pack.baseline_version_ref,
        candidate_version_ref=pack.candidate_version_ref,
        baseline_definition_hashes=[result.baseline_definition_hash],
        candidate_definition_hashes=[result.candidate_definition_hash],
        control_snapshot_ids=[result.control_snapshot_id],
        control_snapshot_fingerprints=[result.control_snapshot_fingerprint],
        baseline_outcome_refs=[result.baseline_outcome_ref],
        candidate_outcome_refs=[result.candidate_outcome_ref],
        status="passed",
        readiness_status="candidate_ready_for_human_gate_review",
        promotion_readiness="manual_gate_only",
        comparison_conclusion="candidate_improved_without_regression",
        pass_rate=1.0,
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        aggregate_baseline_metrics=dict(result.baseline_metrics),
        aggregate_candidate_metrics=dict(result.candidate_metrics),
        aggregate_metric_deltas=dict(result.metric_deltas),
        case_results=[result],
        regression_flags=[],
        limitations=[],
        evidence_refs=[
            "evidence://workflow-eval/run",
            "evidence://workflow-eval/result",
        ],
        blockers=[],
        generated_at=generated_at,
    )
    assert validate_workflow_variant_eval_run(run, case_pack=pack) == []
    return baseline, candidate, registry, pack, run


def _claim_controlled_workflow_eval(
    service: EvolutionLabService,
    baseline: WorkflowProfileVersionContract,
    candidate: WorkflowProfileVersionContract,
    pack: WorkflowVariantEvalCasePackContract,
    run: WorkflowVariantEvalRunContract,
    *,
    claimed_at: str = "2026-08-11T20:00:00Z",
) -> bool:
    return service.claim_workflow_variant_eval_run(
        run_id=run.run_id,
        input_fingerprint=service.workflow_variant_eval_input_fingerprint(pack),
        baseline_version_ref=baseline.workflow_version_id,
        baseline_definition_hash=baseline.definition_hash,
        candidate_version_ref=candidate.workflow_version_id,
        candidate_definition_hash=candidate.definition_hash,
        case_pack_id=pack.case_pack_id,
        case_pack_version=pack.case_pack_version,
        case_pack_fingerprint=workflow_variant_eval_case_pack_fingerprint(pack),
        control_fingerprint=service.workflow_variant_eval_control_fingerprint(pack),
        claimed_at=claimed_at,
    )


def _workflow_eval_run_for_pair(
    service: EvolutionLabService,
    *,
    baseline: WorkflowProfileVersionContract,
    candidate: WorkflowProfileVersionContract,
    pack: WorkflowVariantEvalCasePackContract,
    template: WorkflowVariantEvalRunContract,
) -> WorkflowVariantEvalRunContract:
    pack_fingerprint = workflow_variant_eval_case_pack_fingerprint(pack)
    result = service.evaluate_workflow_variant_case(
        baseline=baseline,
        candidate=candidate,
        case=pack.cases[0],
        case_pack_fingerprint=pack_fingerprint,
    )
    run = replace(
        template,
        case_pack_fingerprint=pack_fingerprint,
        baseline_version_ref=baseline.workflow_version_id,
        candidate_version_ref=candidate.workflow_version_id,
        baseline_definition_hashes=[result.baseline_definition_hash],
        candidate_definition_hashes=[result.candidate_definition_hash],
        control_snapshot_ids=[result.control_snapshot_id],
        control_snapshot_fingerprints=[result.control_snapshot_fingerprint],
        baseline_outcome_refs=[result.baseline_outcome_ref],
        candidate_outcome_refs=[result.candidate_outcome_ref],
        aggregate_baseline_metrics=dict(result.baseline_metrics),
        aggregate_candidate_metrics=dict(result.candidate_metrics),
        aggregate_metric_deltas=dict(result.metric_deltas),
        case_results=[result],
    )
    assert validate_workflow_variant_eval_run(run, case_pack=pack) == []
    return run


def _record_controlled_workflow_eval(
    service: EvolutionLabService,
    *,
    suffix: str = "001",
) -> tuple[
    WorkflowProfileVersionContract,
    WorkflowProfileVersionContract,
    WorkflowProfileVersionRegistryContract,
    WorkflowVariantEvalCasePackContract,
    WorkflowVariantEvalRunContract,
]:
    baseline, candidate, registry, pack, run = _controlled_workflow_eval_artifacts(
        service,
        suffix=suffix,
    )
    service.register_workflow_variant_case_pack(pack, registry=registry)
    assert _claim_controlled_workflow_eval(
        service,
        baseline,
        candidate,
        pack,
        run,
    )
    service.record_workflow_variant_eval_run(run)
    return baseline, candidate, registry, pack, run


def _workflow_release_review_artifacts(
    service: EvolutionLabService,
    *,
    baseline: WorkflowProfileVersionContract,
    candidate: WorkflowProfileVersionContract,
):  # type: ignore[no-untyped-def]
    proposal = service.create_proposal_from_workflow_candidate(candidate)
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-eval/reviewer",
        evidence_refs=["evidence://workflow-eval/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    rollback = service.build_workflow_rollback_plan(
        baseline=baseline,
        candidate=candidate,
        trigger_conditions=["controlled evaluation regression"],
        verification_tests=["test://workflow-eval/rollback"],
        evidence_refs=["evidence://workflow-eval/rollback"],
        operator_ref="operator://workflow-eval/reviewer",
        generated_at="2026-08-11T20:02:00Z",
    )
    return proposal, review, rollback


def test_workflow_variant_eval_store_is_append_only_idempotent_and_restart_safe() -> None:
    database_path = runtime_dir("workflow-eval-persistence") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    baseline, candidate, registry, pack, run = _controlled_workflow_eval_artifacts(
        service
    )

    assert service.register_workflow_variant_case_pack(pack, registry=registry) == pack
    assert service.register_workflow_variant_case_pack(pack, registry=registry) == pack
    with pytest.raises(ValueError, match="identity collision"):
        service.register_workflow_variant_case_pack(
            replace(pack, evidence_refs=[*pack.evidence_refs, "evidence://divergent"]),
            registry=registry,
        )
    assert _claim_controlled_workflow_eval(
        service, baseline, candidate, pack, run
    )
    assert not _claim_controlled_workflow_eval(
        service, baseline, candidate, pack, run
    )
    assert service.record_workflow_variant_eval_run(run) == run
    assert service.record_workflow_variant_eval_run(run) == run

    restarted = EvolutionLabService(database_path=str(database_path))
    assert restarted.get_workflow_variant_eval_run(run.run_id) == run
    assert restarted.list_workflow_variant_eval_runs(
        workflow_profile=run.workflow_profile,
        route=run.route,
        case_pack_id=run.case_pack_id,
        limit=1,
    ) == [run]
    with pytest.raises(ValueError, match="run id collision"):
        restarted.record_workflow_variant_eval_run(
            replace(run, evidence_refs=[*run.evidence_refs, "evidence://divergent"])
        )


def test_workflow_variant_eval_register_requires_attested_registry_and_definitions() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-eval-registry-binding") / "evolution.db")
    )
    baseline, candidate, registry, pack, _run = _controlled_workflow_eval_artifacts(
        service
    )

    unsafe_candidate = replace(candidate, blockers=["unsafe candidate"])
    unsafe_registry = replace(
        registry,
        versions=[
            unsafe_candidate if version == candidate else version
            for version in registry.versions
        ],
    )
    missing_evidence_candidate = replace(
        candidate,
        evidence_refs=[*candidate.evidence_refs, "evidence://not-in-registry"],
    )
    missing_evidence_registry = replace(
        registry,
        versions=[
            missing_evidence_candidate if version == candidate else version
            for version in registry.versions
        ],
    )
    for invalid_registry, blocker in (
        (
            replace(registry, registry_status="baseline_snapshot_ready"),
            "workflow_eval_candidate_registry_required",
        ),
        (unsafe_registry, "workflow_eval_candidate_state_invalid"),
        (
            missing_evidence_registry,
            "workflow_eval_candidate_registry_evidence_mismatch",
        ),
    ):
        with pytest.raises(ValueError, match=blocker):
            service.register_workflow_variant_case_pack(
                pack,
                registry=invalid_registry,
            )

    case = pack.cases[0]
    forged_candidate_steps = [
        *case.candidate_observation.expected_workflow_steps,
        "forged unregistered candidate step",
    ]
    forged_candidate_hash = workflow_definition_hash(
        workflow_steps=forged_candidate_steps,
        workflow_checkpoints=case.candidate_observation.expected_checkpoint_refs,
        workflow_decision_points=case.candidate_observation.expected_decision_points,
        success_criteria=case.candidate_observation.expected_success_criteria,
    )
    forged_pack = replace(
        pack,
        cases=[
            replace(
                case,
                candidate_observation=replace(
                    case.candidate_observation,
                    definition_hash=forged_candidate_hash,
                    expected_workflow_steps=forged_candidate_steps,
                ),
            )
        ],
    )
    with pytest.raises(
        ValueError,
        match="candidate_registry_definition_mismatch",
    ):
        service.register_workflow_variant_case_pack(
            forged_pack,
            registry=registry,
        )

    assert service.register_workflow_variant_case_pack(
        pack,
        registry=registry,
    ) == pack


def test_workflow_variant_eval_claim_is_atomic_and_rejects_binding_drift() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-eval-claim") / "evolution.db")
    )
    baseline, candidate, registry, pack, run = _controlled_workflow_eval_artifacts(
        service
    )
    service.register_workflow_variant_case_pack(pack, registry=registry)

    def claim() -> bool:
        return _claim_controlled_workflow_eval(
            service,
            baseline,
            candidate,
            pack,
            run,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: claim(), range(8)))
    assert results.count(True) == 1
    assert results.count(False) == 7

    with pytest.raises(ValueError, match="run id collision"):
        _claim_controlled_workflow_eval(
            service,
            baseline,
            candidate,
            pack,
            run,
            claimed_at="2026-08-11T20:00:01Z",
        )
    claim_values = {
        "input_fingerprint": service.workflow_variant_eval_input_fingerprint(pack),
        "baseline_version_ref": baseline.workflow_version_id,
        "baseline_definition_hash": baseline.definition_hash,
        "candidate_version_ref": candidate.workflow_version_id,
        "candidate_definition_hash": candidate.definition_hash,
        "case_pack_id": pack.case_pack_id,
        "case_pack_version": pack.case_pack_version,
        "case_pack_fingerprint": workflow_variant_eval_case_pack_fingerprint(pack),
        "control_fingerprint": service.workflow_variant_eval_control_fingerprint(pack),
        "claimed_at": "2026-08-11T20:00:02Z",
    }
    for index, divergent in enumerate(
        (
            {"input_fingerprint": "c" * 64},
            {"baseline_version_ref": "workflow-version://wrong-baseline/1.0.0"},
            {"candidate_definition_hash": "d" * 64},
            {"case_pack_fingerprint": "e" * 64},
            {"control_fingerprint": "f" * 64},
        )
    ):
        with pytest.raises(ValueError, match="does not match"):
            service.claim_workflow_variant_eval_run(
                run_id=f"workflow-variant-eval://software-change/wrong-{index}",
                **{**claim_values, **divergent},
            )


def test_workflow_variant_eval_sql_guards_and_tamper_do_not_starve_listing() -> None:
    database_path = runtime_dir("workflow-eval-sql-guards") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    baseline, candidate, registry, pack, run = _controlled_workflow_eval_artifacts(
        service
    )
    service.register_workflow_variant_case_pack(pack, registry=registry)
    _claim_controlled_workflow_eval(service, baseline, candidate, pack, run)
    service.record_workflow_variant_eval_run(run)
    baseline_2, candidate_2, registry_2, pack_2, run_2 = (
        _controlled_workflow_eval_artifacts(
            service,
            suffix="002",
            generated_at="2026-08-11T20:01:00Z",
        )
    )
    service.register_workflow_variant_case_pack(pack_2, registry=registry_2)
    _claim_controlled_workflow_eval(
        service,
        baseline_2,
        candidate_2,
        pack_2,
        run_2,
        claimed_at="2026-08-11T20:01:00Z",
    )
    service.record_workflow_variant_eval_run(run_2)

    with connect(database_path) as connection:
        for statement in (
            "UPDATE workflow_eval_case_packs SET route = 'tampered'",
            "DELETE FROM workflow_eval_case_packs",
            "UPDATE workflow_eval_run_claims SET input_fingerprint = 'tampered'",
            "DELETE FROM workflow_eval_run_claims",
            "UPDATE workflow_eval_runs SET route = 'tampered'",
            "DELETE FROM workflow_eval_runs",
        ):
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(statement)
        connection.execute("DROP TRIGGER workflow_eval_runs_no_update")
        connection.execute(
            """
            UPDATE workflow_eval_runs
            SET payload_sha256 = ?
            WHERE run_id = ?
            """,
            ("0" * 64, run_2.run_id),
        )
        connection.commit()

    assert service.get_workflow_variant_eval_run(run_2.run_id) is None
    assert service.list_workflow_variant_eval_runs(limit=1) == [run]


def test_workflow_variant_eval_rejects_unclaimed_or_mismatched_run() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-eval-run-binding") / "evolution.db")
    )
    baseline, candidate, registry, pack, run = _controlled_workflow_eval_artifacts(
        service
    )
    service.register_workflow_variant_case_pack(pack, registry=registry)
    with pytest.raises(ValueError, match="requires an existing claim"):
        service.record_workflow_variant_eval_run(run)
    _claim_controlled_workflow_eval(service, baseline, candidate, pack, run)
    with pytest.raises(ValueError, match="invalid workflow variant evaluation run"):
        service.record_workflow_variant_eval_run(
            replace(run, case_pack_fingerprint="f" * 64)
        )


def test_workflow_variant_eval_blocks_stale_workflow_definition_hash() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-eval-stale-definition") / "evolution.db")
    )
    baseline, candidate, _registry, pack, _ = _controlled_workflow_eval_artifacts(
        service
    )
    stale_candidate = replace(
        candidate,
        workflow_steps=[*candidate.workflow_steps, "unhashed mutation"],
    )

    result = service.evaluate_workflow_variant_case(
        baseline=baseline,
        candidate=stale_candidate,
        case=pack.cases[0],
        case_pack_fingerprint=workflow_variant_eval_case_pack_fingerprint(pack),
    )

    assert result.passed is False
    assert "candidate_definition_hash_valid" in result.limitations
    assert "limitations_absent" in result.failures


def test_workflow_release_checklist_rejects_candidate_mutated_after_eval() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-eval-stale-release") / "evolution.db")
    )
    baseline, candidate, registry, pack, run = _controlled_workflow_eval_artifacts(
        service
    )
    service.register_workflow_variant_case_pack(pack, registry=registry)
    _claim_controlled_workflow_eval(service, baseline, candidate, pack, run)
    service.record_workflow_variant_eval_run(run)
    proposal = service.create_proposal_from_workflow_candidate(candidate)
    review = service.review_proposal(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        action="sandbox",
        operator_ref="operator://workflow-eval/reviewer",
        evidence_refs=["evidence://workflow-eval/review"],
        proposed_tests=list(candidate.proposed_tests),
        rollback_plan_ref=candidate.rollback_plan_ref,
    )
    rollback = service.build_workflow_rollback_plan(
        baseline=baseline,
        candidate=candidate,
        trigger_conditions=["controlled evaluation regression"],
        verification_tests=["test://workflow-eval/rollback"],
        evidence_refs=["evidence://workflow-eval/rollback"],
        operator_ref="operator://workflow-eval/reviewer",
        generated_at="2026-08-11T20:02:00Z",
    )

    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        workflow_candidate=replace(
            candidate,
            workflow_steps=[*candidate.workflow_steps, "mutation after evaluation"],
        ),
        workflow_variant_eval=run,
        workflow_rollback_plan=rollback,
    )

    assert "workflow_variant_eval_scope_mismatch" in checklist.blockers
    assert checklist.sandbox_eval_status == "invalid_controlled_evidence"


def test_workflow_release_rejects_candidate_substitution_after_human_review() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-release-substitution") / "evolution.db")
    )
    baseline, reviewed_candidate, registry, pack, template_run = (
        _controlled_workflow_eval_artifacts(service)
    )
    proposal, review, rollback = _workflow_release_review_artifacts(
        service,
        baseline=baseline,
        candidate=reviewed_candidate,
    )

    substituted_steps = [
        *reviewed_candidate.workflow_steps,
        "unreviewed post-review candidate behavior",
    ]
    substituted_candidate = replace(
        reviewed_candidate,
        workflow_steps=substituted_steps,
        definition_hash=workflow_definition_hash(
            workflow_steps=substituted_steps,
            workflow_checkpoints=reviewed_candidate.workflow_checkpoints,
            workflow_decision_points=reviewed_candidate.workflow_decision_points,
            success_criteria=reviewed_candidate.success_criteria,
        ),
    )
    substituted_registry = replace(
        registry,
        versions=[
            substituted_candidate if version == reviewed_candidate else version
            for version in registry.versions
        ],
    )
    source_case = pack.cases[0]
    substituted_case = replace(
        source_case,
        required_candidate_steps=[
            *source_case.required_candidate_steps,
            "unreviewed post-review candidate behavior",
        ],
        candidate_observation=replace(
            source_case.candidate_observation,
            definition_hash=substituted_candidate.definition_hash,
            expected_workflow_steps=list(substituted_candidate.workflow_steps),
        ),
    )
    substituted_pack = replace(pack, cases=[substituted_case])
    substituted_run = _workflow_eval_run_for_pair(
        service,
        baseline=baseline,
        candidate=substituted_candidate,
        pack=substituted_pack,
        template=template_run,
    )
    service.register_workflow_variant_case_pack(
        substituted_pack,
        registry=substituted_registry,
    )
    assert _claim_controlled_workflow_eval(
        service,
        baseline,
        substituted_candidate,
        substituted_pack,
        substituted_run,
    )
    service.record_workflow_variant_eval_run(substituted_run)

    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        workflow_candidate=substituted_candidate,
        workflow_variant_eval=substituted_run,
        workflow_rollback_plan=rollback,
    )

    assert (
        "persisted_workflow_candidate_definition_hash_mismatch"
        in checklist.blockers
    )
    assert "workflow_release_review_candidate_binding_mismatch" in checklist.blockers
    assert "workflow_variant_eval_scope_mismatch" in checklist.blockers
    assert checklist.checklist_status == "blocked"
    assert checklist.sandbox_eval_status == "invalid_controlled_evidence"


def test_workflow_release_rejects_unsafe_candidate_snapshot() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-release-unsafe-candidate") / "evolution.db")
    )
    baseline, candidate, _registry, _pack, run = _record_controlled_workflow_eval(
        service
    )
    proposal, review, rollback = _workflow_release_review_artifacts(
        service,
        baseline=baseline,
        candidate=candidate,
    )
    unsafe_candidate = replace(
        candidate,
        evidence_refs=[],
        proposed_tests=[],
        blockers=["critical candidate blocker"],
        source_registry_fingerprint="0" * 64,
        human_review_required=False,
        sandbox_required=False,
    )

    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        workflow_candidate=unsafe_candidate,
        workflow_variant_eval=run,
        workflow_rollback_plan=rollback,
    )

    assert "workflow_release_candidate_has_blockers" in checklist.blockers
    assert "workflow_release_candidate_state_invalid" in checklist.blockers
    assert "workflow_release_candidate_registry_invalid" in checklist.blockers
    assert "workflow_release_candidate_evidence_invalid" in checklist.blockers
    assert checklist.checklist_status == "blocked"
    assert checklist.sandbox_eval_status == "invalid_controlled_evidence"


def test_workflow_release_revalidates_canonical_baseline_after_store_bypass() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-release-forged-baseline") / "evolution.db")
    )
    baseline, candidate, _registry, pack, template_run = (
        _controlled_workflow_eval_artifacts(service)
    )
    forged_baseline_steps = [
        *baseline.workflow_steps,
        "forged non-canonical baseline behavior",
    ]
    forged_baseline = replace(
        baseline,
        workflow_steps=forged_baseline_steps,
        definition_hash=workflow_definition_hash(
            workflow_steps=forged_baseline_steps,
            workflow_checkpoints=baseline.workflow_checkpoints,
            workflow_decision_points=baseline.workflow_decision_points,
            success_criteria=baseline.success_criteria,
        ),
    )
    source_case = pack.cases[0]
    forged_case = replace(
        source_case,
        baseline_observation=replace(
            source_case.baseline_observation,
            definition_hash=forged_baseline.definition_hash,
            expected_workflow_steps=list(forged_baseline.workflow_steps),
        ),
    )
    forged_pack = replace(pack, cases=[forged_case])
    forged_run = _workflow_eval_run_for_pair(
        service,
        baseline=forged_baseline,
        candidate=candidate,
        pack=forged_pack,
        template=template_run,
    )
    service.repository.register_workflow_variant_case_pack(forged_pack)
    assert _claim_controlled_workflow_eval(
        service,
        forged_baseline,
        candidate,
        forged_pack,
        forged_run,
    )
    service.record_workflow_variant_eval_run(forged_run)
    proposal, review, rollback = _workflow_release_review_artifacts(
        service,
        baseline=baseline,
        candidate=candidate,
    )

    checklist = service.build_sandbox_to_release_checklist(
        proposal,
        review_decision=review,
        workflow_candidate=candidate,
        workflow_variant_eval=forged_run,
        workflow_rollback_plan=rollback,
    )

    assert any(
        blocker.endswith("release_baseline_definition_mismatch")
        for blocker in checklist.blockers
    )
    assert "workflow_variant_eval_scope_mismatch" in checklist.blockers
    assert checklist.checklist_status == "blocked"
    assert checklist.sandbox_eval_status == "invalid_controlled_evidence"


def _workflow_lifecycle_reviewed_release(
    service: EvolutionLabService,
    *,
    suffix: str = "lifecycle-001",
):  # type: ignore[no-untyped-def]
    baseline, candidate, _registry, _pack, run = _record_controlled_workflow_eval(
        service,
        suffix=suffix,
    )
    proposal, _review, _rollback = _workflow_release_review_artifacts(
        service,
        baseline=baseline,
        candidate=candidate,
    )
    return baseline, candidate, proposal, run


def test_workflow_lifecycle_activation_and_human_rollback_are_release_bound() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-lifecycle") / "evolution.db")
    )
    _baseline, candidate, proposal, run = _workflow_lifecycle_reviewed_release(
        service
    )
    external_gates = [
        "standard_engineering_gate",
        "release_gate_before_promotion",
    ]
    activation = service.prepare_workflow_lifecycle_transition(
        action="activate_candidate",
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        workflow_eval_run_id=run.run_id,
        human_authorization_ref="human-authorization://workflow-lifecycle/activate/001",
        operator_ref="operator://workflow-lifecycle/release-manager",
        evidence_refs=["evidence://workflow-lifecycle/activate/001"],
        completed_test_refs=list(candidate.proposed_tests),
        completed_external_gates=external_gates,
        timestamp="2026-08-12T18:00:00Z",
    )

    assert activation.transition_status == "active_promoted"
    assert activation.active_version_ref == candidate.workflow_version_id
    assert activation.revision == 1
    assert service.verify_persisted_workflow_lifecycle_transition(activation)
    assert service.get_workflow_lifecycle_release_bundle(
        activation.transition_id
    ) is not None

    reviewed_proposal = service.repository.fetch_proposal(
        str(proposal.evolution_proposal_id)
    )
    assert reviewed_proposal is not None
    service.repository.record_proposal(
        replace(
            reviewed_proposal,
            expected_gain="later review metadata must not disable safe rollback",
        )
    )
    assert service.verify_persisted_workflow_lifecycle_transition(activation)

    rollback = service.prepare_workflow_lifecycle_transition(
        action="rollback_to_baseline",
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        workflow_eval_run_id=run.run_id,
        human_authorization_ref="human-authorization://workflow-lifecycle/rollback/001",
        operator_ref="operator://workflow-lifecycle/release-manager",
        evidence_refs=["evidence://workflow-lifecycle/rollback/001"],
        completed_test_refs=list(candidate.proposed_tests),
        completed_external_gates=external_gates,
        failure_refs=["failure://workflow-lifecycle/runtime-regression/001"],
        current_transition=activation,
        timestamp="2026-08-12T18:05:00Z",
    )

    assert rollback.transition_status == "baseline_restored"
    assert rollback.active_version_ref == rollback.baseline_version_ref
    assert rollback.previous_transition_id == activation.transition_id
    assert rollback.revision == 2
    assert service.verify_persisted_workflow_lifecycle_transition(rollback)


def test_workflow_lifecycle_blocks_replay_substitution_and_automatic_rollback() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-lifecycle-hostile") / "evolution.db")
    )
    baseline, candidate, proposal, run = _workflow_lifecycle_reviewed_release(
        service,
        suffix="lifecycle-hostile",
    )
    gates = ["standard_engineering_gate", "release_gate_before_promotion"]
    with pytest.raises(ValueError, match="standard and release gates"):
        service.prepare_workflow_lifecycle_transition(
            action="activate_candidate",
            evolution_proposal_id=str(proposal.evolution_proposal_id),
            workflow_eval_run_id=run.run_id,
            human_authorization_ref="human-authorization://missing-release-gate",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/missing-release-gate"],
            completed_test_refs=list(candidate.proposed_tests),
            completed_external_gates=["standard_engineering_gate"],
            timestamp="2026-08-12T18:55:00Z",
        )
    with pytest.raises(ValueError, match="completed tests missing"):
        service.prepare_workflow_lifecycle_transition(
            action="activate_candidate",
            evolution_proposal_id=str(proposal.evolution_proposal_id),
            workflow_eval_run_id=run.run_id,
            human_authorization_ref="human-authorization://missing-tests",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/missing-tests"],
            completed_test_refs=[],
            completed_external_gates=gates,
            timestamp="2026-08-12T18:56:00Z",
        )
    activation = service.prepare_workflow_lifecycle_transition(
        action="activate_candidate",
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        workflow_eval_run_id=run.run_id,
        human_authorization_ref="human-authorization://workflow-lifecycle/activate/hostile",
        operator_ref="operator://workflow-lifecycle/release-manager",
        evidence_refs=["evidence://workflow-lifecycle/activate/hostile"],
        completed_test_refs=list(candidate.proposed_tests),
        completed_external_gates=gates,
        timestamp="2026-08-12T19:00:00Z",
    )

    with pytest.raises(ValueError, match="identity collision"):
        service.prepare_workflow_lifecycle_transition(
            action="activate_candidate",
            evolution_proposal_id=str(proposal.evolution_proposal_id),
            workflow_eval_run_id=run.run_id,
            human_authorization_ref="human-authorization://stale-genesis-replay",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/stale-genesis-replay"],
            completed_test_refs=list(candidate.proposed_tests),
            completed_external_gates=gates,
            timestamp="2026-08-12T19:01:00Z",
        )

    with pytest.raises(ValueError, match="requires failure evidence"):
        service.prepare_workflow_lifecycle_transition(
            action="rollback_to_baseline",
            evolution_proposal_id=str(proposal.evolution_proposal_id),
            workflow_eval_run_id=run.run_id,
            human_authorization_ref="human-authorization://rollback/without-failure",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/rollback/hostile"],
            completed_test_refs=list(candidate.proposed_tests),
            completed_external_gates=gates,
            current_transition=activation,
            timestamp="2026-08-12T19:05:00Z",
        )
    with pytest.raises(ValueError, match="current transition is not persisted"):
        service.prepare_workflow_lifecycle_transition(
            action="rollback_to_baseline",
            evolution_proposal_id=str(proposal.evolution_proposal_id),
            workflow_eval_run_id=run.run_id,
            human_authorization_ref="human-authorization://rollback/forged-current",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/rollback/forged-current"],
            completed_test_refs=list(candidate.proposed_tests),
            completed_external_gates=gates,
            failure_refs=["failure://workflow-lifecycle/forged-current"],
            current_transition=replace(
                activation,
                candidate_definition_hash=baseline.definition_hash,
            ),
            timestamp="2026-08-12T19:05:00Z",
        )
    persisted_proposal = service.repository.fetch_proposal(
        str(proposal.evolution_proposal_id)
    )
    assert persisted_proposal is not None
    artifacts = service._workflow_lifecycle_activation_artifacts(
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        workflow_eval_run_id=run.run_id,
        operator_ref="operator://workflow-lifecycle/release-manager",
        evidence_refs=["evidence://workflow-lifecycle/substitution"],
        completed_external_gates=gates,
        generated_at="2026-08-12T19:10:00Z",
    )
    with pytest.raises(ValueError, match="predecessor release bundle is not persisted"):
        service.build_workflow_lifecycle_transition(
            action="rollback_to_baseline",
            proposal=artifacts["proposal"],
            review_decision=artifacts["review_decision"],
            baseline=artifacts["baseline"],
            candidate=artifacts["candidate"],
            release_checklist=artifacts["release_checklist"],
            promotion_gate=artifacts["promotion_gate"],
            workflow_variant_eval=artifacts["workflow_variant_eval"],
            rollback_plan=artifacts["rollback_plan"],
            human_authorization_ref="human-authorization://synthetic-predecessor",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/synthetic-predecessor"],
            completed_test_refs=list(candidate.proposed_tests),
            failure_refs=["failure://workflow-lifecycle/synthetic-predecessor"],
            current_transition=replace(
                activation,
                transition_id="workflow-lifecycle-transition://synthetic",
            ),
            timestamp="2026-08-12T19:10:00Z",
        )
    forged_candidate = replace(
        candidate,
        workflow_steps=[*candidate.workflow_steps, "unreviewed lifecycle behavior"],
    )
    with pytest.raises(ValueError, match="not release-bound"):
        service.build_workflow_lifecycle_transition(
            action="activate_candidate",
            proposal=persisted_proposal,
            review_decision=artifacts["review_decision"],
            baseline=artifacts["baseline"],
            candidate=forged_candidate,
            release_checklist=artifacts["release_checklist"],
            promotion_gate=artifacts["promotion_gate"],
            workflow_variant_eval=artifacts["workflow_variant_eval"],
            rollback_plan=artifacts["rollback_plan"],
            human_authorization_ref="human-authorization://substitution",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/substitution"],
            completed_test_refs=list(candidate.proposed_tests),
            timestamp="2026-08-12T19:10:00Z",
        )


def test_workflow_lifecycle_release_bundle_is_append_only_and_tamper_evident() -> None:
    database_path = runtime_dir("workflow-lifecycle-store") / "evolution.db"
    service = EvolutionLabService(database_path=str(database_path))
    _baseline, candidate, proposal, run = _workflow_lifecycle_reviewed_release(
        service,
        suffix="lifecycle-store",
    )
    activation = service.prepare_workflow_lifecycle_transition(
        action="activate_candidate",
        evolution_proposal_id=str(proposal.evolution_proposal_id),
        workflow_eval_run_id=run.run_id,
        human_authorization_ref="human-authorization://workflow-lifecycle/store",
        operator_ref="operator://workflow-lifecycle/release-manager",
        evidence_refs=["evidence://workflow-lifecycle/store"],
        completed_test_refs=list(candidate.proposed_tests),
        completed_external_gates=[
            "standard_engineering_gate",
            "release_gate_before_promotion",
        ],
        timestamp="2026-08-12T20:00:00Z",
    )
    with connect(database_path) as connection:
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute(
                "UPDATE workflow_lifecycle_release_bundles SET route = 'tampered'"
            )
        with pytest.raises(IntegrityError, match="append-only"):
            connection.execute("DELETE FROM workflow_lifecycle_release_bundles")
        connection.execute(
            "DROP TRIGGER workflow_lifecycle_release_bundles_no_update"
        )
        connection.execute(
            """
            UPDATE workflow_lifecycle_release_bundles
            SET payload_sha256 = ?
            WHERE transition_id = ?
            """,
            ("0" * 64, activation.transition_id),
        )
        connection.commit()

    assert service.get_workflow_lifecycle_release_bundle(
        activation.transition_id
    ) is None
    assert not service.verify_persisted_workflow_lifecycle_transition(activation)


def test_workflow_lifecycle_release_bundle_exact_retry_is_concurrency_safe() -> None:
    service = EvolutionLabService(
        database_path=str(runtime_dir("workflow-lifecycle-concurrency") / "evolution.db")
    )
    _baseline, candidate, proposal, run = _workflow_lifecycle_reviewed_release(
        service,
        suffix="lifecycle-concurrency",
    )

    def prepare():  # type: ignore[no-untyped-def]
        return service.prepare_workflow_lifecycle_transition(
            action="activate_candidate",
            evolution_proposal_id=str(proposal.evolution_proposal_id),
            workflow_eval_run_id=run.run_id,
            human_authorization_ref="human-authorization://workflow-lifecycle/concurrent",
            operator_ref="operator://workflow-lifecycle/release-manager",
            evidence_refs=["evidence://workflow-lifecycle/concurrent"],
            completed_test_refs=list(candidate.proposed_tests),
            completed_external_gates=[
                "standard_engineering_gate",
                "release_gate_before_promotion",
            ],
            timestamp="2026-08-12T21:00:00Z",
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        transitions = list(executor.map(lambda _: prepare(), range(8)))

    assert all(transition == transitions[0] for transition in transitions)
    assert service.verify_persisted_workflow_lifecycle_transition(transitions[0])
