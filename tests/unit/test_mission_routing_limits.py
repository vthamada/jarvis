"""Bounded integral source review, never truncation or a side-channel wrapper."""

import json
import time
from dataclasses import replace

import pytest

from evals.operator_tasks.canonical_mission_port import CanonicalMissionTaskPort, _request_data
from evals.operator_tasks.corpus import Source
from evals.operator_tasks.runner import Binding, ExecutionRequest


def request():
    return ExecutionRequest(
        Binding("trial", "request-one", "example", "operator-missions-v1", "d" * 64,
                "revision-one", "mission-subject", "mission-session"),
        "Compare documentation reports.", (Source("report", "Documentation is current."),),
        time.monotonic() + 90, None,
    )


@pytest.mark.parametrize("length", [512, 513])
def test_exact_reviewed_bundle_character_limit_is_not_a_source_text_limit(length):
    # The documented bound includes refs, JSON keys and punctuation, not just text.
    empty_bundle = json.dumps({"sources": [{"ref": "report", "text": ""}]},
                              ensure_ascii=False, separators=(",", ":"))
    original = "é" * (length - len(empty_bundle))
    selected = replace(request(), sources=(Source("report", original),))
    if length > 512:
        with pytest.raises(ValueError, match="^canonical_mission_source_limit$"):
            _request_data(selected)
    else:
        brief, bundle = _request_data(selected)
        assert brief == selected.brief and len(bundle) == 512
        assert len(bundle.encode("utf-8")) > len(bundle)
        assert json.loads(bundle)["sources"] == [{"ref": "report", "text": original}]


@pytest.mark.parametrize("change,code", [
    ({"sources": (Source("report", "x" * 513),)}, "canonical_mission_source_limit"),
    ({"sources": (Source("short", "Documentation."), Source("other", "x" * 513))},
     "canonical_mission_source_limit"),
    ({"brief": "Compare " + "x" * 2048}, "invalid_canonical_mission_request"),
    ({"brief": ""}, "invalid_canonical_mission_request"),
    ({"brief": 17}, "invalid_canonical_mission_request"),
    ({"sources": (Source("report", ""),)}, "invalid_canonical_mission_request"),
    ({"sources": (Source("report", 'The field is "api_key": "private-sentinel".'),)},
     "canonical_mission_source_sensitive"),
    ({"sources": (Source("report", "Documentation password=private-sentinel"),)},
     "canonical_mission_source_sensitive"),
    ({"sources": (Source("Bearer private-sentinel", "Documentation."),)},
     "canonical_mission_source_sensitive"),
])
def test_refused_source_or_brief_never_constructs_core_or_writes_runtime(tmp_path, change, code):
    control = CanonicalMissionTaskPort(
        tmp_path, authorized=True,
        core_factory=lambda _: pytest.fail("refused data constructed Core"),
    )
    with pytest.raises(ValueError, match="^" + code + "$"):
        control.execute(replace(request(), **change))
    assert not tuple(tmp_path.iterdir())
    assert control.snapshot()["core_turns"] == 0


def test_brief_and_source_newlines_unicode_and_whitespace_are_not_rewritten():
    selected = replace(request(), brief="Compare documentação reports.\n  ",
                       sources=(Source("report", "Documentation Café\nOlá.  "),))
    brief, bundle = _request_data(selected)
    assert brief == selected.brief
    assert json.loads(bundle)["sources"][0]["text"] == selected.sources[0].text
