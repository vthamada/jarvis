"""Admit bounded fields from pinned REA static JavaScript Evidence as untrusted data.

This projection is not a full REA schema validator, an authenticity check, or an
RFC 8785 semantic-digest verifier. Nested provenance and unconsumed observations
receive JSON resource/type checks only. No graph text, paths, provider labels,
limitations, source code or instructions are copied to the projection summary.
No I/O, process execution, Core dispatch, permissions or memory live here.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_JSON_DEPTH = 24
MAX_COLLECTION_ITEMS = 10000
MAX_JSON_VALUES = 50000
MAX_STRING_BYTES = 65536
MAX_SAFE_INTEGER = 2**53 - 1
_PROVIDER_ID = "rea-javascript-application"
_PROVIDER = {"id": _PROVIDER_ID, "name": "REA JavaScript application analyzer", "version": "1"}
_COVERAGE = {"complete", "partial", "unknown", "unavailable"}
_ENVELOPE_KEYS = {
    "evidence_id", "subject", "provider", "analysis_profile", "predicate_type", "operation",
    "parameters", "raw_result", "normalized_result", "confidence", "authority", "environment",
    "limitations", "relationship_coverage", "locations", "evidence_links",
}
_RESULT_KEYS = {
    "input_path", "format", "root_artifact_sha256", "inventory_manifest_id",
    "inventory_graph_sha256", "integrity_contradictions", "graph", "summary", "statistics",
    "limitations", "semantic_graph",
}
_STATISTICS = {
    "relevant_files", "nested_asar_containers", "text_bytes_read", "invalid_utf8_files",
    "parsed_javascript_files", "visited_ast_nodes", "findings", "modules", "parse_failures",
}
_NODE_KINDS = {
    "package", "installer", "artifact", "asar-entry", "electron-main", "electron-preload",
    "electron-renderer", "electron-utility", "javascript-asset", "javascript-chunk",
    "javascript-module", "javascript-expression", "source-map", "source-module", "browser-window",
    "frame", "target", "context-bridge-api", "ipc-channel", "ipc-handler", "worker",
    "service-worker", "endpoint", "storage", "native-addon", "native-export", "managed-assembly",
    "managed-module", "managed-type", "managed-method", "managed-field", "managed-pinvoke-import",
    "managed-native-implementation", "runtime-script-instance", "unknown",
}
_RELATIONS = {
    "contains", "loads", "imports", "maps_to", "exposes", "sends", "invokes", "handles", "calls",
    "persists_to", "observed_as", "changed_from",
}
_GRAPH_KEYS = {"schema", "graph_id", "root_node_ids", "nodes", "edges", "coverage", "limitations"}
_SEMANTIC_KEYS = {
    "schema", "graph_id", "root_artifact_sha256", "application_graph_id", "root_node_ids",
    "evidence_contexts", "nodes", "relations", "fingerprints", "unknowns", "coverage",
    "limitations",
}


@dataclass(frozen=True, slots=True)
class ReaEvidenceProjection:
    summary: str
    provider_id: str
    root_sha256: str
    semantic_digest_verified: bool = False
    counts: tuple[tuple[str, int], ...] = ()


def _invalid():
    raise ValueError("invalid_rea_evidence")


def _object(value, keys=None):
    if type(value) is not dict or keys is not None and set(value) != keys:
        _invalid()
    return value


def _list(value, *, nonempty=False):
    if type(value) is not list or nonempty and not value:
        _invalid()
    return value


def _text(value):
    if type(value) is not str or not value:
        _invalid()
    return value


def _digest(value, prefix=""):
    if type(value) is not str or re.fullmatch(re.escape(prefix) + "[a-f0-9]{64}", value) is None:
        _invalid()
    return value


def _count(value):
    if type(value) is not int or not 0 <= value <= MAX_SAFE_INTEGER:
        _invalid()
    return value


def _strings(value):
    for item in _list(value):
        _text(item)


def _json_budget(document):
    """Reject cycles, foreign Python objects and excessive input before encoding."""
    ancestors = set()
    values = bytes_seen = 0

    def visit(value, depth):
        nonlocal values, bytes_seen
        values += 1
        if depth > MAX_JSON_DEPTH or values > MAX_JSON_VALUES:
            _invalid()
        if type(value) is str:
            size = len(value.encode("utf-8", errors="strict"))
            if size > MAX_STRING_BYTES:
                _invalid()
            bytes_seen += size
        elif value is None or type(value) is bool:
            bytes_seen += 5
        elif type(value) is int:
            if abs(value) > MAX_SAFE_INTEGER:
                _invalid()
            bytes_seen += 17
        elif type(value) is float:
            if not math.isfinite(value):
                _invalid()
            bytes_seen += 24
        elif type(value) in (dict, list):
            if len(value) > MAX_COLLECTION_ITEMS or id(value) in ancestors:
                _invalid()
            ancestors.add(id(value))
            try:
                if type(value) is dict:
                    for key, item in value.items():
                        if type(key) is not str:
                            _invalid()
                        visit(key, depth + 1)
                        visit(item, depth + 1)
                else:
                    for item in value:
                        visit(item, depth + 1)
            finally:
                ancestors.remove(id(value))
        else:
            _invalid()
        if bytes_seen > MAX_DOCUMENT_BYTES:
            _invalid()

    visit(document, 0)
    encoded = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_DOCUMENT_BYTES:
        _invalid()


def _limits(value):
    for item in _list(value):
        item = _object(item, {"name", "value", "unit"})
        _text(item["name"])
        _count(item["value"])
        if item["unit"] not in {
            "items", "bytes", "milliseconds", "depth", "characters", "instructions", "other",
        }:
            _invalid()


def _coverage(value, *, semantic=False):
    value = _object(value)
    expected = {"status", "truncated", "limits"}
    expected |= (
        {"omitted_nodes", "omitted_relations", "families"} if semantic else {"omitted_count"}
    )
    allowed = expected | ({"omitted_unknown_occurrences"} if semantic else set())
    if not expected <= set(value) <= allowed:
        _invalid()
    status, truncated = value["status"], value["truncated"]
    if type(status) is not str or status not in _COVERAGE or type(truncated) is not bool:
        _invalid()
    _limits(value["limits"])
    if semantic:
        if status == "complete" and truncated:
            _invalid()
        _list(value["families"])
        for key in ("omitted_nodes", "omitted_relations"):
            if value[key] is not None:
                _count(value[key])
    else:
        omitted = value["omitted_count"]
        if omitted is not None:
            _count(omitted)
        if status == "complete" and (truncated or omitted != 0):
            _invalid()
        if status in {"unknown", "unavailable"} and (truncated or omitted is not None):
            _invalid()
        if truncated and (status != "partial" or not value["limits"] or omitted == 0):
            _invalid()
    return status


def _graph(value):
    graph = _object(value, _GRAPH_KEYS)
    if graph["schema"] != "JavaScriptApplicationGraph":
        _invalid()
    _digest(graph["graph_id"], "jag_")
    ids = set()
    for node in _list(graph["nodes"], nonempty=True):
        node = _object(node)
        identifier = _digest(node["node_id"], "jag_node_")
        if identifier in ids or type(node["kind"]) is not str or node["kind"] not in _NODE_KINDS:
            _invalid()
        ids.add(identifier)
        _object(node["identity"])
        _list(node["observations"])
    roots = _list(graph["root_node_ids"], nonempty=True)
    if any(type(item) is not str or item not in ids for item in roots):
        _invalid()
    edge_ids = set()
    imports = 0
    for edge in _list(graph["edges"]):
        edge = _object(edge)
        identifier = _digest(edge["edge_id"], "jag_edge_")
        if (identifier in edge_ids or type(edge["relation"]) is not str
                or edge["relation"] not in _RELATIONS
                or type(edge["source_node_id"]) is not str or edge["source_node_id"] not in ids
                or type(edge["target_node_id"]) is not str or edge["target_node_id"] not in ids):
            _invalid()
        edge_ids.add(identifier)
        imports += int(edge["relation"] == "imports")
    _strings(graph["limitations"])
    return graph, ids, imports, _coverage(graph["coverage"])


def _semantic_graph(value, root_sha, graph, application_ids):
    semantic = _object(value, _SEMANTIC_KEYS)
    if (semantic["schema"] != "JavaScriptSemanticRelationGraph"
            or semantic["root_artifact_sha256"] != root_sha
            or semantic["application_graph_id"] != graph["graph_id"]):
        _invalid()
    _digest(semantic["graph_id"], "jsrg_")
    ids = set()
    nodes = _list(semantic["nodes"], nonempty=True)
    for node in nodes:
        node = _object(node)
        identifier = _digest(node["node_id"], "jsrg_node_")
        if identifier in ids:
            _invalid()
        ids.add(identifier)
        for reference in _list(node["application_node_ids"]):
            if type(reference) is not str or reference not in application_ids:
                _invalid()
    if any(type(item) is not str or item not in ids
           for item in _list(semantic["root_node_ids"], nonempty=True)):
        _invalid()
    for key in ("evidence_contexts", "relations", "fingerprints", "unknowns"):
        _list(semantic[key])
    _strings(semantic["limitations"])
    return _coverage(semantic["coverage"], semantic=True)


def project_evidence(document: dict) -> ReaEvidenceProjection:
    """Return counts/enums only; invalid input always raises a fixed ValueError.

    Admission establishes structural consistency for this projection, not that
    REA actually ran, that its semantic IDs match, or that the application is safe.
    The companion runner must establish execution/provenance separately.
    """
    try:
        _object(document, _ENVELOPE_KEYS)
        _json_budget(document)
        if (_object(document["provider"], {"id", "name", "version"}) != _PROVIDER
                or document["operation"] != "analyze_javascript_application"
                or document["predicate_type"] != "rea.javascript-application-analysis"
                or document["confidence"] != "derived"
                or document["authority"] != "shipped-artifact"
                or document["raw_result"] is not None or document["environment"] is not None):
            _invalid()
        _digest(document["evidence_id"], "ev_")
        profile = document["analysis_profile"]
        if profile is not None:
            _object(profile, {"provider", "parameters", "digest"})
            if _object(profile["provider"], {"id", "name", "version"}) != _PROVIDER:
                _invalid()
            _object(profile["parameters"])
            _digest(profile["digest"])
        result = _object(document["normalized_result"])
        if not _RESULT_KEYS <= set(result) <= _RESULT_KEYS | {"source_selection"}:
            _invalid()
        path = _text(result["input_path"])
        root_sha = _digest(result["root_artifact_sha256"])
        _digest(result["inventory_manifest_id"], "agm_")
        _digest(result["inventory_graph_sha256"])
        subject = _object(
            document["subject"], {"name", "digest", "local_path", "format", "architecture"},
        )
        parameters = _object(document["parameters"])
        if (result["format"] != "directory" or subject["format"] != "directory"
                or subject["architecture"] is not None or subject["local_path"] != path
                or _object(subject["digest"], {"sha256"})["sha256"] != root_sha
                or parameters.get("input_path") != path or parameters.get("format") != "directory"
                or parameters.get("integrity_policy") != "fail"
                or _list(result["integrity_contradictions"])):
            _invalid()
        _text(subject["name"])
        _object(result["summary"])
        _strings(result["limitations"])
        _strings(document["limitations"])
        _list(document["locations"])
        for identifier in _list(document["evidence_links"]):
            _digest(identifier, "ev_")
        relationship = document["relationship_coverage"]
        if relationship is not None and _object(relationship).get("status") not in {
            "complete", "partial", "unknown",
        }:
            _invalid()
        statistics = _object(result["statistics"])
        if not _STATISTICS <= set(statistics) <= _STATISTICS | {"skipped_javascript_files"}:
            _invalid()
        for value in statistics.values():
            _count(value)
        graph, ids, imports, coverage = _graph(result["graph"])
        semantic_coverage = _semantic_graph(result["semantic_graph"], root_sha, graph, ids)
        counts = (
            ("parsed_javascript_files", statistics["parsed_javascript_files"]),
            ("modules", statistics["modules"]), ("imports", imports),
            ("graph_nodes", len(graph["nodes"])), ("graph_edges", len(graph["edges"])),
            ("parse_failures", statistics["parse_failures"]),
        )
        summary = (
            "JavaScript static analysis evidence (read-only): "
            + "; ".join(f"{key}={value}" for key, value in counts)
            + f"; graph_coverage={coverage}; semantic_coverage={semantic_coverage}. "
            + "Semantic digests unverified; static evidence does not prove runtime behavior."
        )
        if len(summary) > 512:
            _invalid()
        return ReaEvidenceProjection(summary, _PROVIDER_ID, root_sha, False, counts)
    except Exception:
        raise ValueError("invalid_rea_evidence") from None
