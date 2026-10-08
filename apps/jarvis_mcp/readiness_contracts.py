"""App-local readonly authored snapshot boundary, never Core authority."""

from __future__ import annotations

import importlib.util
import json
import math
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROTOCOL_VERSION = "2025-11-25"
TOOL_NAME = "read_product_readiness"
SCHEMA_VERSION = "jarvis-mcp-readiness-v1"
FRONT_IDS = tuple(f"F{i:02d}" for i in range(1, 14)) + tuple(f"T{i:02d}" for i in range(1, 4))
SELECTIONS = ("all", *FRONT_IDS)
INVENTORY_REF = "docs/implementation/product-readiness.json"
SERVER_INFO = {"name": "jarvis-readiness", "version": "1.0.0"}
CLIENT_INFO = {"name": "jarvis-readiness-client", "version": "1.0.0"}
MAX_MESSAGE_BYTES = 65536
MAX_SESSION_BYTES = 262144
MAX_SNAPSHOT_BYTES = 24576
MAX_REQUESTS = 32
MAX_EVENTS = 128
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}\Z", re.ASCII)
_TOP = {"schema_version", "front_id", "inventory_ref", "origin", "authority", "evidence_scope",
        "runtime_verified", "product_ready", "snapshot_date", "last_validated_mb", "active_mb",
        "counts", "source_documents", "fronts"}
INPUT_SCHEMA = {"type": "object", "properties": {"front_id": {"type": "string",
                "enum": list(SELECTIONS)}}, "required": ["front_id"],
                "additionalProperties": False}
OUTPUT_SCHEMA = {"type": "object", "properties": {
    "schema_version": {"const": SCHEMA_VERSION}, "front_id": {"enum": list(SELECTIONS)},
    "inventory_ref": {"const": INVENTORY_REF}, "origin": {"const": "local_repository_snapshot"},
    "authority": {"const": "none"}, "evidence_scope": {"const": "authored_snapshot"},
    "runtime_verified": {"const": False}, "product_ready": {"const": False},
    "snapshot_date": {"type": "string"}, "last_validated_mb": {"type": "object"},
    "active_mb": {"type": ["object", "null"]}, "counts": {"type": "object"},
    "source_documents": {"type": "array"}, "fronts": {"type": "array"}},
    "required": sorted(_TOP), "additionalProperties": False}
TOOL_DESCRIPTOR = {"name": TOOL_NAME, "description": "Read the authored local product snapshot.",
                   "inputSchema": INPUT_SCHEMA, "outputSchema": OUTPUT_SCHEMA,
                   "annotations": {"readOnlyHint": True, "destructiveHint": False,
                                   "idempotentHint": True, "openWorldHint": False}}


class ReadinessRejected(ValueError):
    """Fixed diagnostics only; never includes server or inventory text."""


def _reject(code="invalid_readiness_snapshot"):
    raise ReadinessRejected(code)


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            _reject("invalid_json")
        result[key] = value
    return result


def parse_json(raw):
    try:
        if type(raw) is not bytes or len(raw) > MAX_MESSAGE_BYTES:
            _reject("invalid_json")
        return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=_pairs,
                          parse_constant=lambda _: _reject("invalid_json"))
    except (ValueError, UnicodeError, RecursionError, TypeError):
        _reject("invalid_json")


def encode_json(value, *, sort_keys=False):
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False,
                          separators=(",", ":"), sort_keys=sort_keys).encode("utf-8", "strict")
    except (ValueError, UnicodeError, RecursionError, TypeError):
        _reject("invalid_json")


def validate_arguments(arguments):
    if (type(arguments) is not dict or set(arguments) != {"front_id"}
            or type(arguments["front_id"]) is not str or arguments["front_id"] not in SELECTIONS):
        _reject("invalid_tool_arguments")
    return arguments["front_id"]


def readiness_module():
    # Fixed trusted stdlib-only module. -I subprocess does not import cwd/PYTHONPATH.
    path = Path(__file__).resolve().parents[2] / "tools/product_readiness_report.py"
    spec = importlib.util.spec_from_file_location("jarvis_owned_readiness_report", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_snapshot(front_id, *, root=None):
    validate_arguments({"front_id": front_id})
    try:
        module = readiness_module()
        workspace = module.ROOT if root is None else root
        report = module.build_report(module.load_inventory(root=workspace), root=workspace)
        result = {key: value for key, value in report.items() if key != "schema_version"}
        result.update(schema_version=SCHEMA_VERSION, front_id=front_id,
                      inventory_ref=INVENTORY_REF, origin="local_repository_snapshot",
                      authority="none")
        if front_id != "all":
            result["fronts"] = [front for front in result["fronts"] if front["id"] == front_id]
        return validate_snapshot(result, front_id, root=workspace)
    except Exception:
        _reject()


def validate_snapshot(document, front_id, *, root=None):
    """Validate shape/containment, not semantic truth or runtime acceptance."""
    validate_arguments({"front_id": front_id})
    try:
        if (type(document) is not dict or set(document) != _TOP
                or document["schema_version"] != SCHEMA_VERSION
                or document["front_id"] != front_id or document["inventory_ref"] != INVENTORY_REF
                or document["origin"] != "local_repository_snapshot"
                or document["authority"] != "none"
                or document["evidence_scope"] != "authored_snapshot"
                or document["runtime_verified"] is not False
                or document["product_ready"] is not False
                or len(encode_json(document)) > MAX_SNAPSHOT_BYTES):
            _reject()
        module = readiness_module()
        workspace = module.ROOT if root is None else root
        fronts = document["fronts"]
        expected = FRONT_IDS if front_id == "all" else (front_id,)
        if (type(fronts) is not list or len(fronts) != len(expected)
                or any(type(front) is not dict or front.get("id") != identifier
                       for identifier, front in zip(expected, fronts, strict=True))):
            _reject()
        inventory = {key: document[key] for key in (
            "snapshot_date", "evidence_scope", "last_validated_mb", "active_mb",
            "source_documents")}
        inventory.update(schema_version="jarvis-product-readiness-v1", fronts=fronts)
        if front_id == "all":
            module.validate_inventory(inventory, root=workspace)
        else:
            # Reuse the same authored validators without fabricating omitted
            # fronts or claiming that a selected projection validates their data.
            if (type(document["snapshot_date"]) is not str
                    or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}",
                                    document["snapshot_date"]) is None
                    or type(document["source_documents"]) is not list
                    or tuple(document["source_documents"]) != module.SOURCE_DOCUMENTS):
                _reject()
            date.fromisoformat(document["snapshot_date"])
            module._milestone(document["last_validated_mb"], {"done"})
            if document["active_mb"] is not None:
                module._milestone(document["active_mb"], {"ready", "in_progress", "blocked"})
                if document["active_mb"]["id"] == document["last_validated_mb"]["id"]:
                    _reject()
            for reference in document["source_documents"]:
                module._safe_path(reference, workspace)
            front = fronts[0]
            if (set(front) != module._FRONT_KEYS or type(front["status"]) is not str
                    or front["status"] not in module.STATUSES):
                _reject()
            module._text(front["name"], 80)
            for key in ("available", "remaining_acceptance", "evidence"):
                module._strings(front[key])
            for reference in front["evidence"]:
                module._safe_path(reference, workspace)
        counts = document["counts"]
        if (type(counts) is not dict or set(counts) != {
                "product_fronts", "transversal_fronts", "total_fronts", "by_status"}
                or any(type(counts[key]) is not int or counts[key] != value for key, value in (
                    ("product_fronts", 13), ("transversal_fronts", 3), ("total_fronts", 16)))
                or type(counts["by_status"]) is not dict
                or set(counts["by_status"]) != set(module.STATUSES)
                or any(type(count) is not int or not 0 <= count <= 16
                       for count in counts["by_status"].values())
                or sum(counts["by_status"].values()) != 16):
            _reject()
        if front_id == "all" and counts != module.build_report(inventory, root=workspace)["counts"]:
            _reject()
        if front_id != "all" and counts["by_status"][fronts[0]["status"]] < 1:
            _reject()
        return parse_json(encode_json(document))
    except Exception:
        _reject()


@dataclass(frozen=True)
class ReadinessBinding:
    principal_ref: str
    session_ref: str
    scope: tuple[str, ...] = ("readiness.snapshot.read",)

    def __post_init__(self):
        if (any(type(value) is not str or not _REF.fullmatch(value)
                for value in (self.principal_ref, self.session_ref))
                or type(self.scope) is not tuple or self.scope != ("readiness.snapshot.read",)):
            _reject("invalid_binding")


@dataclass(frozen=True)
class ReadinessEvent:
    stage: str
    status: str
    reason: str = ""


@dataclass(frozen=True)
class ReadinessObservation:
    binding: ReadinessBinding
    request_id: int
    front_id: str
    _encoded: bytes = field(repr=False)
    authority: str = "none"
    evidence_mode: str = "local_repository_snapshot"
    server_ref: str = "repository://jarvis-product-readiness"

    def __post_init__(self):
        if (type(self.binding) is not ReadinessBinding or type(self.request_id) is not int
                or not 1 <= self.request_id <= MAX_REQUESTS or type(self._encoded) is not bytes
                or self.authority != "none" or self.evidence_mode != "local_repository_snapshot"
                or self.server_ref != "repository://jarvis-product-readiness"):
            _reject("invalid_observation")
        self.binding.__post_init__()
        validate_arguments({"front_id": self.front_id})

    def snapshot(self):
        self.__post_init__()
        return validate_snapshot(parse_json(self._encoded), self.front_id)

    def metadata(self):
        self.__post_init__()
        return {"request_id": self.request_id, "front_id": self.front_id,
                "tool_name": TOOL_NAME, "authority": self.authority,
                "evidence_mode": self.evidence_mode, "server_ref": self.server_ref,
                "status": "completed", "runtime_verified": False, "product_ready": False}


def validate_timeout(value):
    try:
        if (type(value) not in {int, float} or not math.isfinite(value)
                or not 0.01 <= value <= 10):
            _reject("invalid_timeout")
        return float(value)
    except (OverflowError, TypeError, ValueError):
        _reject("invalid_timeout")
