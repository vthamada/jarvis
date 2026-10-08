"""Offline conversation DOM contracts and the real Node regression suite."""

import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1]
ROOT = WEB.parents[1]


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.labels = {}, set()

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if "id" in fields:
            assert fields["id"] not in self.ids
            self.ids[fields["id"]] = (tag, fields)
        if tag == "label" and "for" in fields:
            self.labels.add(fields["for"])


def test_offline_conversation_controls_start_closed_and_labeled():
    document = (WEB / "index.html").read_text(encoding="utf-8")
    elements = Elements()
    elements.feed(document)
    assert {"conversation-pack-file", "conversation-pack-consent"} <= elements.labels
    assert elements.ids["conversation-pack-panel"][0] == "details"
    assert "checked" not in elements.ids["conversation-pack-consent"][1]
    assert "disabled" in elements.ids["conversation-pack-file"][1]
    assert "disabled" in elements.ids["conversation-pack-clear"][1]
    for name in ("conversation-pack-content", "conversation-pack-turn"):
        assert "hidden" in elements.ids[name][1]
    assert elements.ids["conversation-pack-notice"][1]["aria-live"] == "polite"
    assert elements.ids["conversation-pack-notice"][1]["role"] == "status"
    assert elements.ids["conversation-pack-file"][1]["accept"] == ".json,application/json"
    assert "hashes conferem consistência, não identidade ou autorização" in document
    assert "A conversa de exemplo permanece separada" in document


def test_offline_conversation_uses_text_only_and_no_storage_or_transport():
    source = "\n".join((WEB / name).read_text(encoding="utf-8")
                       for name in ("app.mjs", "conversation-pack.mjs"))
    for forbidden in ("innerHTML", "outerHTML", "insertAdjacentHTML", "eval(", "fetch(",
                      "XMLHttpRequest", "WebSocket", "localStorage", "sessionStorage",
                      "indexedDB", "getUserMedia", "clipboard.write", "sendBeacon"):
        assert forbidden not in source
    assert 'from "./conversation-pack.mjs"' in source
    assert 'byId("conversation-pack-file").disabled = !conversationPackConsent' in source
    assert "if (!conversationPackConsent)" in source
    assert "discardConversationPack();" in source.split('byId("reset")', 1)[1]
    assert "discardConversationPack();" in source.split('window.addEventListener("pagehide"', 1)[1]


def test_offline_conversation_keeps_static_server_boundary():
    from apps.jarvis_web.serve import ASSETS, CSP

    assert ASSETS["/conversation-pack.mjs"][0] == "conversation-pack.mjs"
    assert "connect-src 'none'" in CSP and "form-action 'none'" in CSP
    assert not any("api" in path or "conversation-export" in path for path in ASSETS)


def test_offline_conversation_style_keeps_long_text_and_keyboard_touch_accessible():
    style = (WEB / "styles.css").read_text(encoding="utf-8")
    assert ".conversation-pack-panel button { min-height: 44px; }" in style
    assert "white-space: pre-wrap" in style
    assert "overflow-wrap: anywhere" in style
    assert ".conversation-pack-panel :focus-visible" in style


def test_real_node_frontend_regression_suite():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node unavailable: no JavaScript/browser acceptance inferred")
    files = sorted((WEB / "tests").glob("*.test.mjs"))
    assert (WEB / "tests" / "conversation-pack.test.mjs") in files
    assert (WEB / "tests" / "conversation-pack-app.test.mjs") in files
    completed = subprocess.run(
        [node, "--test", "--test-reporter=tap", *(str(path) for path in files)], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "# fail 0" in completed.stdout
