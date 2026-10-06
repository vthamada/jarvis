"""Static DOM/HTTP boundaries supplement browser and JS flow verification."""

from pathlib import Path

from apps.jarvis_web.serve import ASSETS, CSP
from apps.jarvis_web.tests.test_voice_ui_contract import Elements

ROOT = Path(__file__).resolve().parents[1]


def test_presence_has_explicit_local_audio_controls_and_no_autoplay():
    document = (ROOT / "index.html").read_text(encoding="utf-8")
    elements = Elements()
    elements.feed(document)
    assert elements.ids["particle-sphere"][1]["aria-hidden"] == "true"
    assert "presence-audio-file" in elements.labels
    assert elements.ids["presence-audio-file"][1]["type"] == "file"
    for name in ("presence-play", "presence-stop", "presence-clear"):
        assert "disabled" in elements.ids[name][1]
    assert elements.ids["presence-motion"][1]["aria-pressed"] == "false"
    assert elements.ids["presence-status"][1]["aria-live"] == "polite"
    assert "Não é fala ao vivo do Core" in document
    assert "autoplay" not in document


def test_modules_served_without_relaxing_network_or_microphone_policy():
    assert ASSETS["/particle-sphere.mjs"][0] == "particle-sphere.mjs"
    assert ASSETS["/local-voice-playback.mjs"][0] == "local-voice-playback.mjs"
    assert "connect-src 'none'" in CSP
    sources = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("app.mjs", "particle-sphere.mjs", "local-voice-playback.mjs")
    )
    for forbidden in (
        "fetch(",
        "WebSocket",
        "getUserMedia",
        "MediaRecorder",
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "createObjectURL",
        "file.name",
    ):
        assert forbidden not in sources
    assert "localPlayback.getLevel()" in sources
    assert "localPlayback.clear()" in sources
    assert "localPlayback.stop()" in sources
    assert "localPlayback.dispose()" in sources
    assert "prefers-reduced-motion: reduce" in sources
