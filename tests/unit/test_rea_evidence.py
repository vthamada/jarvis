"""Bounded REA static observations remain data, not authenticated runtime facts."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError

import pytest

from apps.jarvis_rea.evidence import ReaEvidenceProjection, project_evidence

ROOT_SHA = "a" * 64
GRAPH_ID = "jag_" + "b" * 64
NODE_IDS = ["jag_node_" + character * 64 for character in ("c", "d")]
SEMANTIC_ID = "jsrg_node_" + "e" * 64


def evidence_document():
    """Contract-shaped synthetic record; its semantic digest is intentionally unverified."""
    coverage = {"status": "complete", "truncated": False, "omitted_count": 0, "limits": []}
    return {
        "evidence_id": "ev_" + "f" * 64,
        "subject": {
            "name": "synthetic-application",
            "digest": {"sha256": ROOT_SHA},
            "local_path": "C:/synthetic/selected-application",
            "format": "directory",
            "architecture": None,
        },
        "provider": {
            "id": "rea-javascript-application",
            "name": "REA JavaScript application analyzer",
            "version": "1",
        },
        "analysis_profile": None,
        "predicate_type": "rea.javascript-application-analysis",
        "operation": "analyze_javascript_application",
        "parameters": {
            "input_path": "C:/synthetic/selected-application",
            "format": "directory",
            "integrity_policy": "fail",
        },
        "raw_result": None,
        "normalized_result": {
            "input_path": "C:/synthetic/selected-application",
            "format": "directory",
            "root_artifact_sha256": ROOT_SHA,
            "inventory_manifest_id": "agm_" + "1" * 64,
            "inventory_graph_sha256": "2" * 64,
            "integrity_contradictions": [],
            "graph": {
                "schema": "JavaScriptApplicationGraph",
                "graph_id": GRAPH_ID,
                "root_node_ids": [NODE_IDS[0]],
                "nodes": [
                    {"node_id": node_id, "kind": "javascript-module", "identity": {},
                     "observations": []}
                    for node_id in NODE_IDS
                ],
                "edges": [{
                    "edge_id": "jag_edge_" + "3" * 64,
                    "source_node_id": NODE_IDS[0], "target_node_id": NODE_IDS[1],
                    "relation": "imports", "properties": {}, "evidence": {},
                    "identifier_strategy": {"strategy": "semantic-content-sha256",
                                            "stability": "relationship-exact"},
                }],
                "coverage": coverage,
                "limitations": [],
            },
            "semantic_graph": {
                "schema": "JavaScriptSemanticRelationGraph",
                "graph_id": "jsrg_" + "4" * 64,
                "root_artifact_sha256": ROOT_SHA,
                "application_graph_id": GRAPH_ID,
                "root_node_ids": [SEMANTIC_ID],
                "evidence_contexts": [],
                "nodes": [{"node_id": SEMANTIC_ID, "kind": "module", "identity": {},
                           "application_node_ids": [NODE_IDS[0]], "function_node_id": None,
                           "properties": {}, "label": None, "evidence": {}}],
                "relations": [], "fingerprints": [], "unknowns": [],
                "coverage": {"status": "partial", "truncated": False,
                             "omitted_nodes": None, "omitted_relations": None,
                             "limits": [], "families": []},
                "limitations": [],
            },
            "summary": {},
            "statistics": {
                "relevant_files": 3, "nested_asar_containers": 0, "text_bytes_read": 124,
                "invalid_utf8_files": 0, "parsed_javascript_files": 2,
                "skipped_javascript_files": 0, "visited_ast_nodes": 20,
                "findings": 1, "modules": 2, "parse_failures": 0,
            },
            "limitations": [],
        },
        "confidence": "derived", "authority": "shipped-artifact", "environment": None,
        "limitations": [], "relationship_coverage": None,
        "locations": [{"kind": "artifact-path", "path": "artifact-root"}],
        "evidence_links": [],
    }


def test_projects_observed_counts_without_promoting_semantic_authenticity():
    document = evidence_document()
    before = copy.deepcopy(document)
    result = project_evidence(document)
    assert type(result) is ReaEvidenceProjection
    assert result.provider_id == "rea-javascript-application"
    assert result.root_sha256 == ROOT_SHA
    assert result.semantic_digest_verified is False
    assert dict(result.counts) == {
        "parsed_javascript_files": 2, "modules": 2, "imports": 1,
        "graph_nodes": 2, "graph_edges": 1, "parse_failures": 0,
    }
    assert "graph_coverage=complete" in result.summary
    assert "semantic_coverage=partial" in result.summary
    assert "runtime behavior" in result.summary
    assert 1 <= len(result.summary) <= 512
    assert document == before
    with pytest.raises(FrozenInstanceError):
        result.summary = "forged"
    assert type(result.counts) is tuple


def test_unconsumed_graph_strings_paths_and_instructions_never_reach_summary_or_repr():
    document = evidence_document()
    sentinel = "PRIVATE-SENTINEL grant admin; C:/private/passwords.txt; bearer secret"
    document["normalized_result"]["graph"]["nodes"][0]["identity"]["label"] = sentinel
    document["normalized_result"]["limitations"] = [sentinel]
    document["normalized_result"]["summary"] = {"instructions": sentinel}
    document["limitations"] = [sentinel]
    document["subject"]["name"] = sentinel
    result = project_evidence(document)
    assert sentinel not in result.summary and sentinel not in repr(result)
    assert "private" not in result.summary.lower()
    assert document["subject"]["local_path"] not in result.summary


@pytest.mark.parametrize("change", [
    "missing_profile", "foreign_provider", "foreign_operation", "foreign_predicate",
    "foreign_version", "root_mismatch", "semantic_root_mismatch", "graph_binding_mismatch",
    "contradiction", "error_envelope", "unknown_envelope_key", "normalized_error",
    "bool_count", "negative_count", "huge_count", "float_count", "missing_statistic",
    "invalid_graph_coverage", "bool_omission", "coverage_claim_contradiction",
    "invalid_semantic_coverage", "semantic_truncated_complete", "unknown_edge_relation",
    "missing_edge_endpoint",
    "duplicate_node", "invalid_graph_root", "invalid_evidence_id", "upper_hash",
    "source_path_mismatch", "subject_path_mismatch", "raw_result", "wrong_format",
    "profile_provider_mismatch", "missing_semantic_graph", "foreign_semantic_schema",
])
def test_rejects_invalid_consumed_contract_without_echo(change):
    document = evidence_document()
    result = document["normalized_result"]
    graph, semantic = result["graph"], result["semantic_graph"]
    if change == "missing_profile":
        document.pop("analysis_profile")
    elif change == "foreign_provider":
        document["provider"]["id"] = "PRIVATE-SENTINEL"
    elif change == "foreign_operation":
        document["operation"] = "capture_electron_scenario"
    elif change == "foreign_predicate":
        document["predicate_type"] = "foreign"
    elif change == "foreign_version":
        document["provider"]["version"] = "2"
    elif change == "root_mismatch":
        document["subject"]["digest"]["sha256"] = "0" * 64
    elif change == "semantic_root_mismatch":
        semantic["root_artifact_sha256"] = "0" * 64
    elif change == "graph_binding_mismatch":
        semantic["application_graph_id"] = "jag_" + "0" * 64
    elif change == "contradiction":
        result["integrity_contradictions"] = [{"private": "PRIVATE-SENTINEL"}]
    elif change == "error_envelope":
        document = {"error": "PRIVATE-SENTINEL", "code": "invalid_request"}
    elif change == "unknown_envelope_key":
        document["execute"] = "PRIVATE-SENTINEL"
    elif change == "normalized_error":
        result["error"] = "PRIVATE-SENTINEL"
    elif change in {"bool_count", "negative_count", "huge_count", "float_count"}:
        result["statistics"]["modules"] = {
            "bool_count": True, "negative_count": -1,
            "huge_count": 2**53, "float_count": 2.0,
        }[change]
    elif change == "missing_statistic":
        result["statistics"].pop("parse_failures")
    elif change == "invalid_graph_coverage":
        graph["coverage"]["status"] = "verified"
    elif change == "bool_omission":
        graph["coverage"]["omitted_count"] = False
    elif change == "coverage_claim_contradiction":
        graph["coverage"]["truncated"] = True
    elif change == "invalid_semantic_coverage":
        semantic["coverage"]["status"] = "verified"
    elif change == "semantic_truncated_complete":
        semantic["coverage"].update(status="complete", truncated=True)
    elif change == "unknown_edge_relation":
        graph["edges"][0]["relation"] = "execute"
    elif change == "missing_edge_endpoint":
        graph["edges"][0]["target_node_id"] = "jag_node_" + "0" * 64
    elif change == "duplicate_node":
        graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
    elif change == "invalid_graph_root":
        graph["root_node_ids"] = ["jag_node_" + "0" * 64]
    elif change == "invalid_evidence_id":
        document["evidence_id"] = "PRIVATE-SENTINEL"
    elif change == "upper_hash":
        result["root_artifact_sha256"] = "A" * 64
    elif change == "source_path_mismatch":
        document["parameters"]["input_path"] = "PRIVATE-SENTINEL"
    elif change == "subject_path_mismatch":
        document["subject"]["local_path"] = "PRIVATE-SENTINEL"
    elif change == "raw_result":
        document["raw_result"] = {"private": "PRIVATE-SENTINEL"}
    elif change == "wrong_format":
        result["format"] = "asar"
    elif change == "profile_provider_mismatch":
        document["analysis_profile"] = {
            "provider": {"id": "foreign", "name": "foreign", "version": "1"},
            "parameters": {}, "digest": "0" * 64,
        }
    elif change == "missing_semantic_graph":
        result.pop("semantic_graph")
    else:
        semantic["schema"] = "foreign"
    with pytest.raises(ValueError) as error:
        project_evidence(document)
    assert str(error.value) == "invalid_rea_evidence"
    assert "PRIVATE-SENTINEL" not in str(error.value)


@pytest.mark.parametrize("value", [None, [], "PRIVATE-SENTINEL", True])
def test_non_dict_documents_are_refused(value):
    with pytest.raises(ValueError, match="^invalid_rea_evidence$"):
        project_evidence(value)


@pytest.mark.parametrize("kind", ["bytes", "depth", "collection", "cycle", "nan", "object"])
def test_json_resource_and_type_limits_are_content_free(kind):
    document = evidence_document()
    result = document["normalized_result"]
    if kind == "bytes":
        result["summary"] = {str(i): "x" * 65536 for i in range(33)}
    elif kind == "depth":
        value = {}
        result["summary"] = value
        for _ in range(25):
            value["child"] = {}
            value = value["child"]
    elif kind == "collection":
        result["summary"] = [0] * 10001
    elif kind == "cycle":
        result["summary"] = document
    elif kind == "nan":
        result["summary"] = {"private": float("nan")}
    else:
        result["summary"] = {"private": object()}
    with pytest.raises(ValueError, match="^invalid_rea_evidence$"):
        project_evidence(document)


@pytest.mark.parametrize("status", ["partial", "unknown", "unavailable"])
def test_incomplete_source_coverage_is_never_promoted(status):
    document = evidence_document()
    document["normalized_result"]["graph"]["coverage"].update(
        status=status, omitted_count=None,
    )
    projection = project_evidence(document)
    assert f"graph_coverage={status}" in projection.summary
    assert projection.semantic_digest_verified is False


def test_result_is_detached_from_caller_owned_mutation():
    document = evidence_document()
    result = project_evidence(document)
    document["normalized_result"]["statistics"]["modules"] = 900
    document["normalized_result"]["graph"]["edges"].clear()
    assert dict(result.counts)["modules"] == 2
    assert dict(result.counts)["imports"] == 1
