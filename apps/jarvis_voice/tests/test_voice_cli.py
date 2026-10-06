import json

import pytest

from apps.jarvis_voice.__main__ import main


def test_cli_without_consent_does_not_start_capture(capsys):
    assert main([]) == 2
    assert json.loads(capsys.readouterr().out) == {
        "mode": "isolated_voice_fixture", "error_code": "consent_required",
    }


@pytest.mark.parametrize("scenario,status,code", [
    ("completed", "completed", 0), ("interrupted", "interrupted", 0),
    ("incomplete", "error", 1), ("silence", "error", 1),
])
def test_cli_scenarios_explicitly_simulated(capsys, scenario, status, code):
    assert main(["--consent", "--scenario", scenario]) == code
    projection = json.loads(capsys.readouterr().out)
    assert projection["state"] == status
    assert projection["mode"] == "isolated_voice_fixture"
    assert projection["hardware_audio"] is False
    assert projection["voice_identity"] == "synthetic_fixture"
    assert projection["tool_authority"] == "none"
