"""Campaign validation plus explicit Linux-only real synthetic stage coverage."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tools.linux_validation import persistent_scenario as scenario


@pytest.mark.parametrize("stage", ["invalid", "../prepare", "/validation", "", "persistent-suite"])
def test_main_refuses_invalid_stage_without_filesystem_access(monkeypatch, stage):
    monkeypatch.setattr(scenario, "run_stage", lambda *_: pytest.fail("must not run"))
    assert scenario.main(stage) == 2


def test_main_windows_never_creates_fixture_or_invokes_kernel(monkeypatch):
    real_run_stage = scenario.run_stage
    monkeypatch.setattr(scenario.sys, "platform", "win32")
    monkeypatch.setattr(scenario, "run_stage", lambda *_: pytest.fail("must not run"))
    assert scenario.main("prepare") == 2
    with pytest.raises(ValueError, match="linux_stage_required"):
        real_run_stage("prepare", Path("nonexistent-fixture"))


def test_main_passes_only_fixed_volume_root_to_internal_seam(monkeypatch, capsys):
    monkeypatch.setattr(scenario.sys, "platform", "linux")
    calls = []

    def run(stage, root):
        calls.append((stage, root))
        return {"stage": stage, "contains_content": False}

    monkeypatch.setattr(scenario, "run_stage", run)
    assert scenario.main("verify") == 0
    assert calls == [("verify", Path("/validation"))]
    assert json.loads(capsys.readouterr().out)["contains_content"] is False


def test_fixture_serialization_is_bounded_and_rejects_nan():
    assert json.loads(scenario._fixture_bytes({"stage": "prepare"})) == {"stage": "prepare"}
    with pytest.raises(ValueError, match="fixture_limit"):
        scenario._fixture_bytes({"metadata": "x" * scenario.FIXTURE_LIMIT})
    with pytest.raises(ValueError):
        scenario._fixture_bytes({"metadata": float("nan")})


def test_command_uses_explicit_identity_roots_opt_in_and_exact_authorization(tmp_path):
    args = scenario._command(
        tmp_path,
        "execute",
        request_id="synthetic",
        challenge_id="challenge",
        action_fingerprint="digest",
        confirmation_receipt_id="receipt",
        show_diff=False,
    )
    assert args[:3] == ["physical", "--runtime-dir", str(tmp_path / "runtime")]
    assert "--enable-execution" in args and "--show-diff" not in args
    assert args[args.index("--operator-identity-ref") + 1] == scenario.OPERATOR
    assert args[args.index("--root") + 1] == f"notes={tmp_path / 'notes'}"
    assert args[-6:] == [
        "--challenge-id",
        "challenge",
        "--action-fingerprint",
        "digest",
        "--confirmation-receipt-id",
        "receipt",
    ]


linux_only = pytest.mark.skipif(
    sys.platform != "linux", reason="real Linux physical campaign required"
)


@linux_only
def test_private_fixture_refuses_wrong_order_hardlink_symlink_and_permissions(tmp_path):
    tmp_path.chmod(0o700)
    fixture = {"schema_version": "persistent-physical-scenario/v1", "stage": "prepare"}
    scenario._save_fixture(tmp_path, fixture)
    target = tmp_path / "fixture.json"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert scenario._load_fixture(tmp_path, "confirm") == fixture
    with pytest.raises(ValueError, match="stage_order"):
        scenario._load_fixture(tmp_path, "recover")
    target.chmod(0o644)
    with pytest.raises(ValueError, match="fixture_invalid"):
        scenario._load_fixture(tmp_path, "confirm")
    target.chmod(0o600)
    linked = tmp_path / "linked"
    os.link(target, linked)
    with pytest.raises(ValueError, match="fixture_invalid"):
        scenario._load_fixture(tmp_path, "confirm")
    linked.unlink()
    target.rename(linked)
    target.symlink_to(linked)
    with pytest.raises(OSError):
        scenario._load_fixture(tmp_path, "confirm")


@linux_only
def test_real_cli_campaign_recovers_hard_process_exit_and_independent_rollback(tmp_path):
    """Actual processes and local disk, not a container/power-loss attestation."""
    tmp_path.chmod(0o700)
    assert scenario.run_stage("prepare", tmp_path)["contains_content"] is False
    assert scenario.run_stage("confirm", tmp_path)["status"] == "passed"
    code = (
        "import sys; from pathlib import Path; "
        "from tools.linux_validation.persistent_scenario import run_stage; "
        "run_stage('crash', Path(sys.argv[1]))"
    )
    result = subprocess.run(
        [str(Path(sys.executable).resolve()), "-c", code, str(tmp_path)],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == scenario.CRASH_EXIT_CODE, result.stderr
    assert json.loads(result.stdout)["power_loss_proof"] is False
    assert scenario.V1.strip() not in result.stdout and str(tmp_path) not in result.stdout
    for stage in ("recover", "rollback", "verify"):
        result = scenario.run_stage(stage, tmp_path)
        assert result["status"] == "passed" and result["power_loss_proof"] is False
    assert (tmp_path / "notes" / "note.txt").read_bytes() == scenario.V1.encode()
    stored = (tmp_path / "fixture.json").read_text()
    assert scenario.V1.strip() not in stored and scenario.V2.strip() not in stored
    assert json.loads(stored)["stage"] == "verify"


@linux_only
def test_prepare_refuses_reusing_nonempty_volume_and_unprotected_root(tmp_path):
    tmp_path.chmod(0o755)
    with pytest.raises(ValueError, match="private_root_required"):
        scenario.run_stage("prepare", tmp_path)
    tmp_path.chmod(0o700)
    (tmp_path / "existing").touch()
    with pytest.raises(ValueError, match="empty_volume_required"):
        scenario.run_stage("prepare", tmp_path)
