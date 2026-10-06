from __future__ import annotations

from dataclasses import asdict, replace
from hashlib import sha256
from json import dumps, loads
from os import link
from pathlib import Path

import pytest
from evolution_lab.service import EvolutionLabService

from shared.contracts import (
    TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
    TechnologyExperimentControlSnapshotContract,
    TechnologyRadarIntakeContract,
)
from shared.technology_experiment import (
    technology_experiment_control_fingerprint,
    technology_experiment_pack_fingerprint,
    technology_experiment_text_fingerprint,
)
from shared.technology_radar_intake import technology_radar_review_subject_fingerprint
from tools import technology_experiment as tool


class _MemoryEvolution:
    def __init__(self, intake: TechnologyRadarIntakeContract) -> None:
        self.intake = intake
        self.pack = None
        self.claim = None
        self.run = None
        self.calls: list[str] = []

    def get_technology_radar_intake(self, **_filters):  # type: ignore[no-untyped-def]
        self.calls.append("get_intake")
        return self.intake

    def register_technology_experiment_pack(self, pack):  # type: ignore[no-untyped-def]
        self.calls.append("register_pack")
        self.pack = pack
        return pack

    def get_technology_experiment_pack(self, **_filters):  # type: ignore[no-untyped-def]
        self.calls.append("get_pack")
        return self.pack

    def claim_technology_experiment_eval_run(self, claim):  # type: ignore[no-untyped-def]
        self.calls.append("claim_run")
        if self.claim is not None:
            return False
        self.claim = claim
        return True

    def record_technology_experiment_eval_run(self, run):  # type: ignore[no-untyped-def]
        self.calls.append("record_run")
        self.run = run
        return run

    def get_technology_experiment_eval_run(self, **_filters):  # type: ignore[no-untyped-def]
        self.calls.append("get_run")
        return self.run


def _write_json(root: Path, payload: object, *, name: str = "manifest.json") -> Path:
    path = root / name
    path.write_text(dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _intake(**overrides: object) -> TechnologyRadarIntakeContract:
    provisional = TechnologyRadarIntakeContract(
        intake_id="technology-intake://handoff-pattern/1.0.0",
        candidate_ref="technology-candidate://handoff-pattern",
        intake_version="1.0.0",
        technology_name="External Handoff Reference",
        source_kind="repository",
        source_locator="https://example.com/handoff-reference",
        source_version_ref="git-commit://handoff-reference/0123456789abcdef",
        source_content_sha256="1" * 64,
        license_id="MIT",
        license_status="declared",
        license_evidence_ref="license-evidence://handoff-reference/mit",
        retrieved_at="2026-08-12T10:00:00Z",
        claims=["Bounded handoffs can reduce rework."],
        risks=["A foreign runtime must remain subordinate."],
        absorption_class="sandbox_experiment",
        target_gap_refs=["KNW-006"],
        research_approval_ref="research-approval://technology-radar/2026-08-12",
        reviewed_payload_fingerprint="0" * 64,
        reviewer_ref="operator://technology-radar-reviewer",
        review_status="approved_for_radar_intake",
        review_evidence_refs=["review-evidence://handoff-reference/1.0.0"],
        reviewed_at="2026-08-12T10:05:00Z",
        recorded_at="2026-08-12T10:06:00Z",
    )
    provisional = replace(provisional, **overrides)
    return replace(
        provisional,
        reviewed_payload_fingerprint=technology_radar_review_subject_fingerprint(
            provisional
        ),
    )


def _pack_selection(intake: TechnologyRadarIntakeContract | None = None) -> dict[str, object]:
    source = intake or _intake()
    control = TechnologyExperimentControlSnapshotContract(
        control_snapshot_id="technology-experiment-control://handoff/1.0.0",
        input_fingerprint="2" * 64,
        sandbox_policy_ref="technology-sandbox-policy://offline-attestation/1.0.0",
        sandbox_policy_version="1.0.0",
        evaluator_version="1.0.0",
        deterministic_seed=7,
        fixed_clock="2026-08-12T10:10:00Z",
        isolation_profile_ref=TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
        isolation_fingerprint="3" * 64,
        environment_fingerprint="4" * 64,
    )
    control_payload = asdict(control)
    for default_field in (
        "offline_only",
        "sandbox_only",
        "read_only",
        "network_fetch_allowed",
        "subprocess_allowed",
        "dependency_installation_allowed",
        "external_code_execution_allowed",
        "tool_dispatch_allowed",
        "host_filesystem_write_allowed",
        "knowledge_ingestion_allowed",
        "memory_write_allowed",
        "runtime_activation_allowed",
        "registry_write_allowed",
        "release_authorized",
        "promotion_authorized",
        "automatic_promotion_allowed",
        "core_mutation_allowed",
        "priority_mutation_allowed",
    ):
        control_payload.pop(default_field)
    control_fingerprint = technology_experiment_control_fingerprint(control)
    checks = {"sovereign_consumer_preserved": True}
    isolation = {
        "dependencies_unchanged": True,
        "external_code_not_executed": True,
        "host_filesystem_unchanged": True,
        "network_disabled": True,
    }

    def observation(arm: str) -> dict[str, object]:
        candidate = arm == "candidate"
        return {
            "observation_id": f"technology-experiment-observation://handoff/{arm}",
            "case_id": "technology-experiment-case://handoff/1.0.0",
            "case_version": "1.0.0",
            "arm": arm,
            "definition_ref": (
                "jarvis-experiment-definition://handoff/1.0.0"
                if candidate
                else "jarvis-baseline://handoff/1.0.0"
            ),
            "definition_hash": "6" * 64 if candidate else "5" * 64,
            "input_fingerprint": "2" * 64,
            "control_snapshot_id": control.control_snapshot_id,
            "control_snapshot_fingerprint": control_fingerprint,
            "outcome_ref": f"technology-experiment-outcome://handoff/{arm}",
            "outcome_status": "completed",
            "contract_checks": checks,
            "isolation_checks": isolation,
            "success_criteria_results": {"bounded_handoff": candidate},
            "action_count": 4,
            "rework_count": 0 if candidate else 2,
            "evidence_refs": [
                f"technology-experiment-evidence://handoff/{arm}/observation",
                f"technology-experiment-evidence://handoff/{arm}/control",
            ],
            "limitations": [],
            "observed_at": control.fixed_clock,
        }

    return {
        "experiment_pack_id": "technology-experiment-pack://handoff/1.0.0",
        "pack_version": "1.0.0",
        "intake_id": source.intake_id,
        "intake_version": source.intake_version,
        "intake_fingerprint": tool.technology_radar_intake_fingerprint(source),
        "translation_kind": "absorbable_pattern",
        "pattern_id": "technology-pattern://bounded-handoff",
        "pattern_name": "Bounded handoff",
        "pattern_summary": "Translate only bounded handoff semantics.",
        "selected_claim_fingerprints": [
            technology_experiment_text_fingerprint(source.claims[0])
        ],
        "selected_risk_fingerprints": [
            technology_experiment_text_fingerprint(source.risks[0])
        ],
        "hypothesis": "A bounded handoff contract reduces rework.",
        "expected_gain": "Reduce rework without expanding authority.",
        "sovereign_consumer_kind": "jarvis_component",
        "sovereign_consumer_ref": "jarvis-component://orchestrator-service",
        "consumer_contract_ref": "jarvis-contract://bounded-handoff/1.0.0",
        "bounded_integration_seam": "jarvis-seam://orchestrator/handoff",
        "target_gap_refs": ["KNW-006"],
        "baseline_definition_ref": "jarvis-baseline://handoff/1.0.0",
        "baseline_definition_hash": "5" * 64,
        "candidate_definition_ref": "jarvis-experiment-definition://handoff/1.0.0",
        "candidate_definition_hash": "6" * 64,
        "isolation_profile_ref": TECHNOLOGY_EXPERIMENT_ISOLATION_PROFILE,
        "risk_control_refs": ["technology-risk-control://no-execution"],
        "mitigation_refs": ["technology-mitigation://discard-pack"],
        "stop_condition_refs": ["technology-stop-condition://authority-drift"],
        "rollback_plan_ref": "technology-experiment-rollback://handoff/1.0.0",
        "rollback_steps": ["Discard the inert experiment pack."],
        "rollback_verification_refs": ["technology-rollback-check://no-runtime-change"],
        "selection_review_ref": "technology-experiment-selection-review://handoff/1.0.0",
        "selected_by_ref": "operator://technology-experiment-reviewer",
        "cases": [
            {
                "case_id": "technology-experiment-case://handoff/1.0.0",
                "case_version": "1.0.0",
                "scenario_ref": "technology-experiment-scenario://handoff",
                "input_fingerprint": "2" * 64,
                "baseline_definition_ref": "jarvis-baseline://handoff/1.0.0",
                "baseline_definition_hash": "5" * 64,
                "candidate_definition_ref": "jarvis-experiment-definition://handoff/1.0.0",
                "candidate_definition_hash": "6" * 64,
                "critical_contract_check_refs": ["sovereign_consumer_preserved"],
                "critical_isolation_check_refs": list(isolation),
                "success_criteria_refs": ["bounded_handoff"],
                "control_snapshot": control_payload,
                "baseline_observation": observation("baseline"),
                "candidate_observation": observation("candidate"),
                "evidence_refs": ["technology-experiment-evidence://handoff/case"],
                "limitations": [],
            }
        ],
        "required_pass_rate": 1.0,
        "evidence_refs": ["technology-experiment-evidence://handoff/selection"],
        "generated_at": "2026-08-12T10:10:00Z",
    }


def _load(path: Path, root: Path) -> dict[str, object]:
    return tool._load_local_manifest_payload(
        path,
        manifest_root=root,
        expected_manifest_sha256=_digest(path),
        max_bytes=4096,
        manifest_label="technology experiment test manifest",
    )


def test_local_manifest_loader_accepts_only_the_detached_reviewed_bytes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "manifests"
    root.mkdir()
    path = _write_json(root, {"pack_id": "technology-experiment://handoff/1.0.0"})
    digest = _digest(path)

    assert tool._load_local_manifest_payload(
        path.name,
        manifest_root=root,
        expected_manifest_sha256=digest,
        max_bytes=4096,
        manifest_label="technology experiment test manifest",
    ) == {"pack_id": "technology-experiment://handoff/1.0.0"}

    path.write_text('{"pack_id":"technology-experiment://swapped/1.0.0"}', encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        tool._load_local_manifest_payload(
            path,
            manifest_root=root,
            expected_manifest_sha256=digest,
            max_bytes=4096,
            manifest_label="technology experiment test manifest",
        )


@pytest.mark.parametrize(
    "raw",
    [
        '{"pack_id":"one","pack_id":"two"}',
        '{"nested":{"case_id":"one","case_id":"two"}}',
        '{"value":NaN}',
        '{"value":Infinity}',
        "[]",
        "\ufeff{}",
    ],
)
def test_local_manifest_loader_rejects_ambiguous_or_noncanonical_json(
    tmp_path: Path,
    raw: str,
) -> None:
    root = tmp_path / "manifests"
    root.mkdir()
    path = root / "invalid.json"
    path.write_text(raw, encoding="utf-8")

    with pytest.raises(ValueError, match="manifest"):
        _load(path, root)


@pytest.mark.parametrize(
    "payload",
    [
        {"command": "run candidate"},
        {"nested": {"module": "foreign.runtime"}},
        {"candidate_module_ref": "foreign-runtime://candidate"},
        {"package": "foreign-framework"},
        {"path": "relative/candidate.py"},
        {"url": "https://example.com/candidate"},
        {"claim": "api_key=do-not-persist-this"},
        {"claims": ["safe", "Bearer do-not-persist-this"]},
        {"api_key": "short-secret"},
        {"evidence": "C:/Users/operator/private/result.json"},
        {"evidence": "ghp_1234567890abcdefghijklmnopqrstuv"},
    ],
)
def test_local_manifest_loader_rejects_executable_fields_and_sensitive_material(
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    root = tmp_path / "manifests"
    root.mkdir()
    path = _write_json(root, payload)

    with pytest.raises(ValueError, match="forbidden field|sensitive (?:field|material)"):
        _load(path, root)


def test_local_manifest_loader_rejects_traversal_symlink_and_hardlink(
    tmp_path: Path,
) -> None:
    root = tmp_path / "manifests"
    root.mkdir()
    outside = _write_json(tmp_path, {"pack_id": "technology-experiment://outside/1.0.0"})

    with pytest.raises(ValueError, match="inside manifest root"):
        _load(outside, root)

    valid = _write_json(root, {"pack_id": "technology-experiment://inside/1.0.0"})
    (root / "nested").mkdir()  # POSIX resolves nested before reaching '..'.
    with pytest.raises(ValueError, match="traversal or streams"):
        _load(root / "nested" / ".." / valid.name, root)

    linked = root / "hardlink.json"
    link(outside, linked)
    with pytest.raises(ValueError, match="hard links"):
        _load(linked, root)

    symlink = root / "symlink.json"
    try:
        symlink.symlink_to(outside)
    except OSError:
        return
    with pytest.raises(ValueError, match="symlink"):
        _load(symlink, root)


@pytest.mark.parametrize(
    "unsafe_root",
    [
        r"\\host\share\technology-experiments",
        r"\\?\C:\technology-experiments",
        r"\\.\GLOBALROOT\Device\HarddiskVolumeShadowCopy1",
        r"\??\C:\technology-experiments",
    ],
)
def test_local_manifest_loader_rejects_remote_or_device_root_before_access(
    unsafe_root: str,
) -> None:
    with pytest.raises(ValueError, match="local non-device path"):
        tool._load_local_manifest_payload(
            "manifest.json",
            manifest_root=unsafe_root,
            expected_manifest_sha256="0" * 64,
            max_bytes=4096,
            manifest_label="technology experiment test manifest",
        )


@pytest.mark.parametrize("stable_metadata", [False, True])
def test_local_manifest_loader_detects_same_size_toctou_before_any_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stable_metadata: bool,
) -> None:
    root = tmp_path / "manifests"
    root.mkdir()
    path = _write_json(root, {"value": "first"})
    expected_digest = _digest(path)
    original_read = tool._read_bounded

    def read_then_swap(stream, *, max_bytes: int):  # type: ignore[no-untyped-def]
        raw = original_read(stream, max_bytes=max_bytes)
        path.write_text('{"value": "other"}', encoding="utf-8")
        return raw

    monkeypatch.setattr(tool, "_read_bounded", read_then_swap)
    if stable_metadata:
        # Declared metadata seam; real I/O still must detect content mutation.
        monkeypatch.setattr(tool, "_require_same_file", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="changed while being read"):
        tool._load_local_manifest_payload(
            path,
            manifest_root=root,
            expected_manifest_sha256=expected_digest,
            max_bytes=4096,
            manifest_label="technology experiment test manifest",
        )


def test_schema_helpers_reject_bool_as_int_duplicates_and_derived_eval_claims() -> None:
    with pytest.raises(ValueError, match="must be False"):
        tool._require_exact_bool(0, field_name="execution_allowed", expected=False)
    with pytest.raises(ValueError, match="duplicates"):
        tool._require_string_list(
            ["CASE-A", "case-a"],
            field_name="case_ids",
        )
    with pytest.raises(ValueError, match="caller-derived field"):
        tool._reject_dangerous_manifest_content(
            {"case": {"metrics": {"success_score": 1.0}}},
            manifest_label="technology experiment eval manifest",
            reject_derived_keys=True,
        )


def test_repository_technology_eval_case_universe_is_canonical_and_inert() -> None:
    eval_path = (
        Path(__file__).resolve().parents[2]
        / "evals"
        / "technology"
        / "technology_experiment_cases_v1.json"
    )
    payload = loads(eval_path.read_text(encoding="utf-8"))

    assert set(payload) == {
        "case_pack_id",
        "case_pack_version",
        "cases",
        "declarative_only",
        "offline_only",
        "sandbox_only",
    }
    assert payload["declarative_only"] is True
    assert payload["offline_only"] is True
    assert payload["sandbox_only"] is True
    assert len(payload["cases"]) == 1
    case = payload["cases"][0]
    assert case["critical_contract_check_refs"] == [
        "sovereign_consumer_preserved"
    ]
    assert set(case["critical_isolation_check_refs"]) == {
        "dependencies_unchanged",
        "external_code_not_executed",
        "host_filesystem_unchanged",
        "network_disabled",
    }
    tool._reject_dangerous_manifest_content(
        payload,
        manifest_label="repository technology eval case universe",
    )


def test_pack_manifest_resolves_source_and_license_only_from_persisted_intake(
    tmp_path: Path,
) -> None:
    intake = _intake()
    selection = _pack_selection(intake)
    assert "source_locator" not in selection
    assert "source_content_sha256" not in selection
    assert "license_id" not in selection
    assert "license_status" not in selection
    root = tmp_path / "manifests"
    root.mkdir()
    manifest = _write_json(root, selection, name="pack.json")
    evolution = _MemoryEvolution(intake)

    result = tool.register_technology_experiment_pack_manifest(
        manifest,
        manifest_root=root,
        expected_manifest_sha256=_digest(manifest),
        intake_reader=evolution,
        evolution_service=evolution,
    )

    assert result.pack.source_content_sha256 == intake.source_content_sha256
    assert result.pack.license_id == intake.license_id
    assert result.pack.license_status == "declared"
    assert result.pack_fingerprint == technology_experiment_pack_fingerprint(result.pack)
    assert evolution.calls == ["get_intake", "get_intake", "register_pack"]
    assert result.source_fetched is False
    assert result.dependency_installed is False
    assert result.candidate_imported is False
    assert result.candidate_executed is False
    assert result.core_called is False
    assert result.tool_dispatched is False
    assert result.runtime_activated is False
    assert result.promotion_performed is False


def test_pack_manifest_is_fully_validated_before_any_intake_or_writer_call(
    tmp_path: Path,
) -> None:
    root = tmp_path / "manifests"
    root.mkdir()
    unsafe = _pack_selection()
    unsafe["command"] = "install foreign-framework"
    manifest = _write_json(root, unsafe)
    evolution = _MemoryEvolution(_intake())

    with pytest.raises(ValueError, match="forbidden field"):
        tool.register_technology_experiment_pack_manifest(
            manifest,
            manifest_root=root,
            expected_manifest_sha256=_digest(manifest),
            intake_reader=evolution,
            evolution_service=evolution,
        )

    assert evolution.calls == []
    assert evolution.pack is None


def test_pack_rejects_unresolved_license_and_intake_fingerprint_swap(
    tmp_path: Path,
) -> None:
    unresolved = _intake(license_id="NOASSERTION", license_status="unknown_requires_review")
    selection = _pack_selection(unresolved)
    root = tmp_path / "manifests"
    root.mkdir()
    manifest = _write_json(root, selection)
    reader = _MemoryEvolution(unresolved)

    with pytest.raises(ValueError, match="resolved declared license"):
        tool.assess_technology_experiment_pack_manifest(
            manifest,
            manifest_root=root,
            expected_manifest_sha256=_digest(manifest),
            intake_reader=reader,
        )

    selection["intake_fingerprint"] = "f" * 64
    swapped = _write_json(root, selection, name="swapped.json")
    with pytest.raises(ValueError, match="binding mismatch"):
        tool.assess_technology_experiment_pack_manifest(
            swapped,
            manifest_root=root,
            expected_manifest_sha256=_digest(swapped),
            intake_reader=reader,
        )
    assert reader.pack is None


def test_eval_manifest_derives_metrics_status_and_exact_retry_without_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake = _intake()
    evolution = _MemoryEvolution(intake)
    root = tmp_path / "manifests"
    root.mkdir()
    pack_manifest = _write_json(root, _pack_selection(intake), name="pack.json")
    registered = tool.register_technology_experiment_pack_manifest(
        pack_manifest,
        manifest_root=root,
        expected_manifest_sha256=_digest(pack_manifest),
        intake_reader=evolution,
        evolution_service=evolution,
    )
    eval_payload = {
        "run_id": "technology-experiment-run://handoff/1.0.0",
        "experiment_pack_id": registered.pack.experiment_pack_id,
        "pack_version": registered.pack.pack_version,
        "pack_fingerprint": registered.pack_fingerprint,
        "generated_at": "2026-08-12T10:11:00Z",
    }
    eval_manifest = _write_json(root, eval_payload, name="eval.json")

    def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("external execution boundary must not be called")

    monkeypatch.setattr("os.system", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)

    first = tool.run_technology_experiment_eval_manifest(
        eval_manifest,
        manifest_root=root,
        expected_manifest_sha256=_digest(eval_manifest),
        pack_reader=evolution,
        evolution_service=evolution,
    )
    replay = tool.run_technology_experiment_eval_manifest(
        eval_manifest,
        manifest_root=root,
        expected_manifest_sha256=_digest(eval_manifest),
        pack_reader=evolution,
        evolution_service=evolution,
    )

    assert replay == first
    assert first.status == "passed_sandbox_only"
    assert first.readiness_status == "eligible_for_human_experiment_review"
    assert first.promotion_readiness == "not_applicable"
    assert first.comparison_conclusion == "candidate_pattern_improved_without_regression"
    assert first.aggregate_candidate_metrics["success_score"] == 1.0
    assert first.aggregate_baseline_metrics["success_score"] == 0.0
    assert first.aggregate_metric_deltas["rework_rate"] == 0.5
    assert first.promotion_authorized is False
    assert first.execution_allowed is False
    assert evolution.calls.count("record_run") == 1


@pytest.mark.parametrize(
    "source_intake",
    [
        None,
        _intake(intake_id="technology-intake://spoofed-reference/1.0.0"),
    ],
)
def test_eval_manifest_requires_the_exact_verified_intake_binding(
    tmp_path: Path,
    source_intake: TechnologyRadarIntakeContract | None,
) -> None:
    intake = _intake()
    evolution = _MemoryEvolution(intake)
    root = tmp_path / "manifests"
    root.mkdir()
    pack_manifest = _write_json(root, _pack_selection(intake), name="pack.json")
    registered = tool.register_technology_experiment_pack_manifest(
        pack_manifest,
        manifest_root=root,
        expected_manifest_sha256=_digest(pack_manifest),
        intake_reader=evolution,
        evolution_service=evolution,
    )
    eval_manifest = _write_json(
        root,
        {
            "run_id": "technology-experiment-run://handoff/binding/1.0.0",
            "experiment_pack_id": registered.pack.experiment_pack_id,
            "pack_version": registered.pack.pack_version,
            "pack_fingerprint": registered.pack_fingerprint,
            "generated_at": "2026-08-12T10:11:00Z",
        },
        name="eval.json",
    )
    evolution.intake = source_intake  # type: ignore[assignment]

    with pytest.raises(ValueError, match="exact persisted intake|verified intake"):
        tool.prepare_technology_experiment_eval_manifest(
            eval_manifest,
            manifest_root=root,
            expected_manifest_sha256=_digest(eval_manifest),
            pack_reader=evolution,
        )

    assert evolution.claim is None
    assert evolution.run is None


def test_failed_preproduced_observation_cannot_derive_a_passing_run(
    tmp_path: Path,
) -> None:
    intake = _intake()
    selection = _pack_selection(intake)
    case = selection["cases"][0]  # type: ignore[index]
    candidate = case["candidate_observation"]  # type: ignore[index]
    candidate["outcome_status"] = "failed"  # type: ignore[index]
    evolution = _MemoryEvolution(intake)
    root = tmp_path / "manifests"
    root.mkdir()
    pack_manifest = _write_json(root, selection, name="pack.json")
    registered = tool.register_technology_experiment_pack_manifest(
        pack_manifest,
        manifest_root=root,
        expected_manifest_sha256=_digest(pack_manifest),
        intake_reader=evolution,
        evolution_service=evolution,
    )
    eval_manifest = _write_json(
        root,
        {
            "run_id": "technology-experiment-run://handoff/failed-candidate/1.0.0",
            "experiment_pack_id": registered.pack.experiment_pack_id,
            "pack_version": registered.pack.pack_version,
            "pack_fingerprint": registered.pack_fingerprint,
            "generated_at": "2026-08-12T10:11:00Z",
        },
        name="eval.json",
    )

    run = tool.run_technology_experiment_eval_manifest(
        eval_manifest,
        manifest_root=root,
        expected_manifest_sha256=_digest(eval_manifest),
        pack_reader=evolution,
        evolution_service=evolution,
    )

    assert run.status == "blocked"
    assert run.readiness_status == "blocked"
    assert run.case_results[0].candidate_outcome_status == "failed"
    assert run.case_results[0].candidate_metrics["success_score"] == 0.0
    assert "candidate_outcome_completed" in run.case_results[0].failures


@pytest.mark.parametrize(
    "fixed_clock",
    ["2026-08-12T10:05:00Z", "2099-01-01T00:00:00Z"],
)
def test_pack_manifest_rejects_invalid_evidence_chronology_before_writer(
    tmp_path: Path,
    fixed_clock: str,
) -> None:
    intake = _intake()
    selection = _pack_selection(intake)
    case = selection["cases"][0]  # type: ignore[index]
    control_payload = case["control_snapshot"]  # type: ignore[index]
    control_payload["fixed_clock"] = fixed_clock  # type: ignore[index]
    control = TechnologyExperimentControlSnapshotContract(**control_payload)  # type: ignore[arg-type]
    control_fingerprint = technology_experiment_control_fingerprint(control)
    for arm in ("baseline", "candidate"):
        observation = case[f"{arm}_observation"]  # type: ignore[index]
        observation["observed_at"] = fixed_clock  # type: ignore[index]
        observation["control_snapshot_fingerprint"] = control_fingerprint  # type: ignore[index]
    selection["generated_at"] = fixed_clock
    evolution = _MemoryEvolution(intake)
    root = tmp_path / "manifests"
    root.mkdir()
    manifest = _write_json(root, selection)

    with pytest.raises(ValueError, match="predate|future"):
        tool.register_technology_experiment_pack_manifest(
            manifest,
            manifest_root=root,
            expected_manifest_sha256=_digest(manifest),
            intake_reader=evolution,
            evolution_service=evolution,
        )

    assert "register_pack" not in evolution.calls
    assert evolution.pack is None


def test_manifest_helpers_end_to_end_with_real_evolution_and_no_runtime_side_effects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake = _intake()
    database = tmp_path / "evolution.db"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    evolution = EvolutionLabService(str(database))
    evolution.register_technology_radar_intake(intake)

    def forbidden(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("technology experiment helpers crossed a runtime boundary")

    monkeypatch.setattr("os.system", forbidden)
    monkeypatch.setattr("subprocess.run", forbidden)
    monkeypatch.setattr("subprocess.Popen", forbidden)
    monkeypatch.setattr("urllib.request.urlopen", forbidden)
    monkeypatch.setattr("socket.socket", forbidden)

    pack_manifest = _write_json(
        manifests,
        _pack_selection(intake),
        name="pack.json",
    )
    reviewed_pack_bytes = pack_manifest.read_bytes()
    registration = tool.register_technology_experiment_pack_manifest(
        pack_manifest,
        manifest_root=manifests,
        expected_manifest_sha256=_digest(pack_manifest),
        intake_reader=evolution,
        evolution_service=evolution,
    )
    assert evolution.get_technology_experiment_pack(
        experiment_pack_id=registration.pack.experiment_pack_id,
        pack_version=registration.pack.pack_version,
    ) == registration.pack

    eval_manifest = _write_json(
        manifests,
        {
            "run_id": "technology-experiment-run://handoff/real-store/1.0.0",
            "experiment_pack_id": registration.pack.experiment_pack_id,
            "pack_version": registration.pack.pack_version,
            "pack_fingerprint": registration.pack_fingerprint,
            "generated_at": "2026-08-12T10:11:00Z",
        },
        name="eval.json",
    )
    reviewed_eval_bytes = eval_manifest.read_bytes()
    run = tool.run_technology_experiment_eval_manifest(
        eval_manifest,
        manifest_root=manifests,
        expected_manifest_sha256=_digest(eval_manifest),
        pack_reader=evolution,
        evolution_service=evolution,
    )

    assert evolution.get_technology_experiment_eval_run(run_id=run.run_id) == run
    assert evolution.list_recent_proposals() == []
    assert pack_manifest.read_bytes() == reviewed_pack_bytes
    assert eval_manifest.read_bytes() == reviewed_eval_bytes
    assert sorted(
        path.relative_to(tmp_path).as_posix()
        for path in tmp_path.rglob("*")
        if path.is_file()
    ) == ["evolution.db", "manifests/eval.json", "manifests/pack.json"]


@pytest.mark.parametrize(
    "spoof",
    [
        {"metrics": {"success_score": 1.0}},
        {"status": "passed_sandbox_only"},
        {"promotion_authorized": True},
        {"command": "run candidate"},
    ],
)
def test_eval_manifest_rejects_caller_derived_or_executable_fields_before_store(
    tmp_path: Path,
    spoof: dict[str, object],
) -> None:
    root = tmp_path / "manifests"
    root.mkdir()
    payload = {
        "run_id": "technology-experiment-run://handoff/1.0.0",
        "experiment_pack_id": "technology-experiment-pack://handoff/1.0.0",
        "pack_version": "1.0.0",
        "pack_fingerprint": "1" * 64,
        "generated_at": "2026-08-12T10:11:00Z",
        **spoof,
    }
    manifest = _write_json(root, payload)
    evolution = _MemoryEvolution(_intake())

    with pytest.raises(ValueError, match="field|schema mismatch"):
        tool.run_technology_experiment_eval_manifest(
            manifest,
            manifest_root=root,
            expected_manifest_sha256=_digest(manifest),
            pack_reader=evolution,
            evolution_service=evolution,
        )

    assert evolution.calls == []
