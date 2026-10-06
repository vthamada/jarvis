"""DOM contract for the explicit fixture voice rehearsal, without browser claims."""

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.labels = set()

    def handle_starttag(self, tag, attributes):
        values = dict(attributes)
        if "id" in values:
            assert values["id"] not in self.ids
            self.ids[values["id"]] = (tag, values)
        if tag == "label" and "for" in values:
            self.labels.add(values["for"])


def test_fixture_voice_controls_have_explicit_labels_and_safe_defaults():
    document = (ROOT / "index.html").read_text(encoding="utf-8")
    elements = Elements()
    elements.feed(document)
    assert {"voice-consent", "voice-transcript", "voice-scenario"} <= elements.labels
    checkbox = elements.ids["voice-consent"][1]
    assert checkbox["type"] == "checkbox"
    assert "checked" not in checkbox
    assert "disabled" in elements.ids["voice-start"][1]
    assert "hidden" in elements.ids["voice-review"][1]
    assert "hidden" in elements.ids["voice-final"][1]
    assert elements.ids["voice-notice"][1]["aria-live"] == "polite"
    assert elements.ids["voice-transcript"][1]["maxlength"] == "4000"
    assert "Sem microfone, áudio, Core, voz clonada ou envio externo" in document
    assert "Confirmar texto não autoriza ações" in document


def test_fixture_voice_assets_have_no_capture_provider_or_audio_egress():
    sources = "\n".join(
        (ROOT / name).read_text(encoding="utf-8") for name in ["app.mjs", "voice-controller.mjs"]
    )
    for forbidden in [
        "getUserMedia",
        "MediaRecorder",
        "AudioContext",
        "SpeechRecognition",
        "speechSynthesis",
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "new Audio(",
    ]:
        assert forbidden not in sources
    assert "import { createVoiceController, handleVoicePageHide }" in sources
    assert 'from "./voice-controller.mjs"' in sources
    assert "textContent = state.finalText" in sources
    assert "exactText: true" in sources


def test_voice_ui_retains_visible_focus_and_full_touch_targets():
    style = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert ".voice-panel button,.voice-panel select{min-height:44px}" in style
    assert ".voice-panel textarea:focus-visible" in style
    assert "outline:2px solid var(--accent)" in style
