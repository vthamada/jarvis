"""Static transcript DOM/adapter contracts, not rendered browser evidence."""

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


def test_transcript_controls_labeled_inert_and_not_authentication():
    document = (ROOT / "index.html").read_text(encoding="utf-8")
    elements = Elements()
    elements.feed(document)
    assert {"transcript-consent", "transcript-file", "transcript-text", "transcript-package"} <= (
        elements.labels)
    assert elements.ids["transcript-panel"][0] == "details"
    consent = elements.ids["transcript-consent"][1]
    assert consent["type"] == "checkbox" and "checked" not in consent
    assert consent["aria-describedby"] == "transcript-help"
    source = elements.ids["transcript-file"][1]
    assert source["type"] == "file" and "disabled" in source
    assert source["accept"] == ".json,application/json"
    for identifier in ("transcript-export", "transcript-cancel"):
        assert "disabled" in elements.ids[identifier][1]
    for identifier in ("transcript-form", "transcript-output"):
        assert "hidden" in elements.ids[identifier][1]
    assert elements.ids["transcript-notice"][1]["aria-live"] == "polite"
    assert elements.ids["transcript-notice"][1]["role"] == "status"
    assert "Origem não verificada" in document
    assert "Sem upload, microfone ou envio ao Core pelo browser" in document
    assert "Confirmar texto não autoriza ações" in document
    assert "não é ticket, receipt ou permissão" in document
    assert "transcript-review --authorized --include-content" in document


def test_transcript_code_point_limit_package_readonly_and_labels():
    document = (ROOT / "index.html").read_text(encoding="utf-8")
    elements = Elements()
    elements.feed(document)
    # HTML maxlength counts UTF-16 units. 8,000 permits the controller's 4,000
    # code-point limit even when every point occupies a surrogate pair.
    assert elements.ids["transcript-text"][1]["maxlength"] == "8000"
    assert "readonly" in elements.ids["transcript-package"][1]
    assert elements.ids["transcript-output"][1]["aria-labelledby"] == "transcript-output-title"
    assert elements.ids["transcript-select"][1]["type"] == "button"
    assert elements.ids["transcript-text"][1]["aria-describedby"] == "transcript-revision"
    source = (ROOT / "transcript-review.mjs").read_text(encoding="utf-8")
    assert "MAX_TEXT_POINTS = 4000" in source
    assert "[...text].length > MAX_TEXT_POINTS" in source


def test_transcript_adapter_no_egress_storage_capture_or_html_sink():
    source = "\n".join((ROOT / name).read_text(encoding="utf-8")
                       for name in ("app.mjs", "transcript-review.mjs"))
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon", "localStorage",
                      "sessionStorage", "indexedDB", "innerHTML", "outerHTML",
                      "insertAdjacentHTML", "getUserMedia", "MediaRecorder", "SpeechRecognition",
                      "clipboard.write", "createObjectURL", "console.log("):
        assert forbidden not in source
    assert 'from "./transcript-review.mjs"' in source
    assert 'byId("transcript-package").value = transcriptPackage' in source
    assert 'byId("transcript-notice").textContent' in source
    assert "review_revision: revision" in source
    assert 'source_origin: "unverified"' in source


def test_adapter_preserves_crlf_until_explicit_edit_and_export_fences():
    source = (ROOT / "app.mjs").read_text(encoding="utf-8")
    assert 'byId("transcript-text").addEventListener("input"' in source
    assert "transcript.revise(event.target.value)" in source
    assert r'byId("transcript-text").value !== view.text.replace(/\r\n?/gu, "\n")' in source
    assert "revision: view.revision, text: view.text" in source
    assert 'typeof result !== "string" || completed.state !== "exported"' in source
    assert "completed.generation !== view.generation + 1" in source
    assert 'byId("transcript-select").focus()' in source


def test_reset_revocation_pagehide_clear_exported_package_and_file():
    source = (ROOT / "app.mjs").read_text(encoding="utf-8")
    assert 'byId("transcript-consent").addEventListener("change"' in source
    assert "transcript.setConsent(event.target.checked)" in source
    assert ('transcriptPackage = ""; transcript.cancel(); '
            'byId("transcript-file").value = ""') in source
    assert ('transcriptPackage = ""; transcript.reset(); '
            'byId("transcript-file").value = ""') in source
    pagehide = source.split('window.addEventListener("pagehide"', 1)[1]
    assert 'transcriptPackage = ""; byId("transcript-file").value = ""' in pagehide
    assert "handleTranscriptPageHide(transcript, event)" in pagehide
    controller = (ROOT / "transcript-review.mjs").read_text(encoding="utf-8")
    assert "if (persisted) controller.reset()" in controller
    assert "else controller.dispose()" in controller


def test_transcript_uses_existing_accessible_touch_and_focus_rules():
    style = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert ".voice-panel button,.voice-panel select{min-height:44px}" in style
    assert ".voice-panel textarea:focus-visible" in style
    assert "outline:2px solid var(--accent)" in style
