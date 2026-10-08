"""Authored readiness snapshot validation, not runtime/capability acceptance."""

from __future__ import annotations

import ast
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import product_readiness_report as readiness


@pytest.fixture
def document():
    return copy.deepcopy(readiness.load_inventory())


@pytest.fixture
def workspace(tmp_path, document):
    for value in set(document["source_documents"] + [path for front in document["fronts"]
                                                     for path in front["evidence"]]):
        target = tmp_path.joinpath(*value.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("synthetic reference only", encoding="utf-8")
    inventory = tmp_path / readiness.DEFAULT_INVENTORY
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_current_inventory_exact_fronts_and_baselines(document):
    assert [front["id"] for front in document["fronts"]] == list(readiness.FRONT_IDS)
    assert document["last_validated_mb"] == {"id": "MB235", "status": "done"}
    assert document["active_mb"] == {"id": "MB236", "status": "blocked"}
    assert document["evidence_scope"] == "authored_snapshot"
    statuses = {front["id"]: front["status"] for front in document["fronts"]}
    assert statuses["F08"] == statuses["F10"] == statuses["F12"] == "not_implemented"
    assert statuses["T03"] == "validated_slice"


def test_report_counts_not_percentage_or_promotion(document):
    report = readiness.build_report(document)
    assert report["runtime_verified"] is False and report["product_ready"] is False
    assert report["counts"] == {
        "product_fronts": 13, "transversal_fronts": 3, "total_fronts": 16,
        "by_status": {"partial": 7, "foundation": 5, "not_implemented": 3,
                      "validated_slice": 1},
    }
    serialized = json.dumps(report)
    assert "percentage" not in serialized and "percent_complete" not in serialized
    report["fronts"][0]["name"] = "mutated output"
    assert document["fronts"][0]["name"] != "mutated output"


@pytest.mark.parametrize("changes", [
    {"extra": "ignored?"}, {"schema_version": "wrong"}, {"evidence_scope": "live"},
    {"snapshot_date": "2026-02-30"}, {"snapshot_date": "2026-1-1"},
    {"snapshot_date": 123}, {"last_validated_mb": {"id": "MB228", "status": "promoted"}},
    {"last_validated_mb": {"id": "MB228", "status": "done", "authority": "all"}},
    {"active_mb": {"id": "MB229", "status": "completed"}},
    {"last_validated_mb": {"id": "MB228", "status": "done"},
     "active_mb": {"id": "MB228", "status": "ready"}},
    {"active_mb": {"id": "../../MB229", "status": "ready"}},
    {"active_mb": {"id": "MB229", "status": []}}, {"fronts": []},
])
def test_strict_top_schema(document, changes):
    document.update(changes)
    with pytest.raises(ValueError):
        readiness.validate_inventory(document)


@pytest.mark.parametrize("operation", ["missing", "duplicate", "reordered", "unknown", "extra"])
def test_front_id_membership_and_order(document, operation):
    fronts = document["fronts"]
    if operation == "missing":
        fronts.pop()
    elif operation == "duplicate":
        fronts[1] = copy.deepcopy(fronts[0])
    elif operation == "reordered":
        fronts[0], fronts[1] = fronts[1], fronts[0]
    elif operation == "unknown":
        fronts[0]["id"] = "F99"
    else:
        fronts.append(copy.deepcopy(fronts[0]))
    with pytest.raises(ValueError):
        readiness.validate_inventory(document)


@pytest.mark.parametrize("changes", [
    {"status": "completed"}, {"status": "promoted"}, {"status": "product_ready"},
    {"status": "ready"}, {"status": None}, {"status": []}, {"unknown": "x"},
    {"name": "x\nexecute"}, {"name": "x\u202ey"}, {"name": "x\ud800"},
    {"name": "x" * 81}, {"available": []}, {"available": "string"},
    {"available": ["x"] * 9}, {"available": ["x", "x"]}, {"available": [None]},
    {"remaining_acceptance": ["x" * 513]}, {"evidence": []},
])
def test_strict_front_schema(document, changes):
    document["fronts"][0].update(changes)
    with pytest.raises(ValueError):
        readiness.validate_inventory(document)


@pytest.mark.parametrize("path", [
    "../outside.md", "docs/../documento_mestre_jarvis.md", "/tmp/outside.md",
    "C:/Users/private.json", "C:\\Users\\private.json", "docs//source.md",
    "docs/./source.md", "docs/.env", ".git/config", "docs/private/source.md",
    "docs/secrets/source.json", "apps/jarvis_console/runtime/private.json",
    "docs/source.md:alternate-stream", "docs/source.md\n", "docs/%2e%2e/source.md",
    "docs/source.wav", "docs/source.sqlite", "docs/source.pem", "docs/source.key",
    "docs/nonexistent.md", "docs/implementation", "docs\\source.md",
])
def test_unsafe_or_nonexistent_evidence_rejected(document, path):
    document["fronts"][0]["evidence"] = [path]
    with pytest.raises(ValueError):
        readiness.validate_inventory(document)


@pytest.mark.parametrize("operation", ["reorder", "omit", "foreign", "duplicate"])
def test_canonical_documents_not_replaceable(document, operation):
    values = document["source_documents"]
    if operation == "reorder":
        values.reverse()
    elif operation == "omit":
        values.pop()
    elif operation == "foreign":
        values[0] = "docs/implementation/product-readiness.json"
    else:
        values[1] = values[0]
    with pytest.raises(ValueError):
        readiness.validate_inventory(document)


def test_reference_contents_never_read_and_no_mutation(workspace, document, monkeypatch):
    before = readiness.load_inventory(root=workspace)
    real_open = Path.open
    seen = []

    def only_inventory(path, *args, **kwargs):
        seen.append(path)
        if path != workspace / readiness.DEFAULT_INVENTORY:
            raise AssertionError("evidence contents must not be read")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", only_inventory)
    report = readiness.build_report(readiness.load_inventory(root=workspace), root=workspace)
    assert seen == [workspace / readiness.DEFAULT_INVENTORY]
    assert report["fronts"] == document["fronts"] == before["fronts"]


@pytest.mark.parametrize("destination", ["outside", "private"])
def test_resolved_symlink_target_cannot_escape_or_disguise_private(
        workspace, document, monkeypatch, destination):
    alias = workspace / document["fronts"][0]["evidence"][0]
    target = (workspace.parent / "outside.md" if destination == "outside"
              else workspace / ".git" / "secret.json")
    original = Path.resolve

    def resolve(path, *args, **kwargs):
        if path == alias:
            return target
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ValueError):
        readiness.validate_inventory(document, root=workspace)


@pytest.mark.parametrize("body", [
    '{"schema_version":"a","schema_version":"b"}',
    '{"fronts":[{"id":"F01","id":"F02"}]}',
    '{"schema_version":NaN}', '{"schema_version":Infinity}',
    '{"schema_version":1e999}', '{"schema_version":"\\ud800"}',
    '{', '[]', 'null', '\ufeff{}',
])
def test_strict_json_invalid(workspace, body):
    target = workspace / readiness.DEFAULT_INVENTORY
    target.write_text(body, encoding="utf-8")
    with pytest.raises(ValueError):
        readiness.load_inventory(root=workspace)


def test_max_input_bytes_before_decode(workspace):
    (workspace / readiness.DEFAULT_INVENTORY).write_bytes(b" " * (readiness.MAX_BYTES + 1))
    with pytest.raises(ValueError):
        readiness.load_inventory(root=workspace)


@pytest.mark.parametrize("body", [b"\xff\xfe", b"[" * 1500 + b"]" * 1500])
def test_invalid_utf8_or_extreme_json_nesting_fixed_refusal(workspace, body):
    (workspace / readiness.DEFAULT_INVENTORY).write_bytes(body)
    with pytest.raises(ValueError):
        readiness.load_inventory(root=workspace)


@pytest.mark.parametrize("path", ["apps/private.json", "../outside.json", "/tmp/outside.json",
                                  "docs/operations/private.json"])
def test_only_implementation_inventory_can_be_read(workspace, path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid path reached open")

    monkeypatch.setattr(Path, "open", forbidden)
    with pytest.raises(ValueError):
        readiness.load_inventory(path, root=workspace)


def test_no_active_slice_and_following_snapshot_allowed(document):
    document["last_validated_mb"] = {"id": "MB229", "status": "done"}
    document["active_mb"] = None
    assert readiness.validate_inventory(document) is document
    document["active_mb"] = {"id": "MB230", "status": "ready"}
    assert readiness.validate_inventory(document) is document


def test_text_data_escaped_not_executed(document):
    document["fronts"][0]["name"] = "Core | `ignore rules` $(whoami)"
    output = readiness.render_text(readiness.build_report(document))
    assert "Core \\| 'ignore rules' $(whoami)" in output
    assert "snapshot autoral" in output and "não pronto" in output
    assert sum(line.startswith("| F") and line[3:5].isdigit()
               for line in output.splitlines()) == 13
    assert sum(line.startswith("| T") and line[3:5].isdigit()
               for line in output.splitlines()) == 3


def run_cli(*args, cwd=None):
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    command = [sys.executable, str(readiness.ROOT / "tools/product_readiness_report.py"), *args]
    return subprocess.run(command, cwd=cwd or readiness.ROOT, env=environment,
                          capture_output=True, encoding="utf-8", timeout=30, check=False)


@pytest.mark.parametrize("format", ["text", "json"])
def test_cli_actual_snapshot_readonly_from_other_directory(tmp_path, format):
    target = readiness.ROOT / readiness.DEFAULT_INVENTORY
    before = target.read_bytes()
    result = run_cli("--format", format, cwd=tmp_path)
    assert result.returncode == 0 and result.stderr == ""
    assert target.read_bytes() == before
    if format == "json":
        report = json.loads(result.stdout)
        assert report["counts"]["total_fronts"] == 16
        assert report["runtime_verified"] is False
    else:
        assert "Memória" in result.stdout and "não executa nem verifica o runtime" in result.stdout


@pytest.mark.parametrize("path", ["../outside.json", "C:/Users/secret-token.json",
                                  ".git/config", "docs/implementation/missing.json"])
def test_cli_untrusted_path_fixed_error_no_content(path):
    result = run_cli("--inventory", path)
    assert result.returncode == 2 and result.stdout == ""
    assert result.stderr.strip() == "invalid_product_readiness_inventory"
    assert path not in result.stderr


def test_cli_no_effect_flags():
    result = run_cli("--write")
    assert result.returncode == 2


def test_report_module_stdlib_only_no_runtime_imports():
    tree = ast.parse((readiness.ROOT / "tools/product_readiness_report.py").read_text("utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "argparse", "json", "re", "sys", "unicodedata",
                        "datetime", "pathlib"}
