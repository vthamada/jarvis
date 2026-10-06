"""Presentation contracts; actual viewport/interaction proof is recorded separately."""

from html.parser import HTMLParser

from apps.jarvis_web.tests.test_voice_ui_contract import ROOT, Elements


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.prompts = []
        self.anchors = []
        self.stack = []
        self.parents = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.parents[values["id"]] = tuple(self.stack)
        if "data-prompt" in values:
            self.prompts.append((tag, values))
        if tag == "a" and "nav-item" in values.get("class", ""):
            self.anchors.append(values["href"])
        if tag not in {"meta", "link", "input", "br"}:
            self.stack.append((tag, values.get("id"), values.get("class", "")))

    def handle_endtag(self, tag):
        assert self.stack[-1][0] == tag
        self.stack.pop()


def test_design_keeps_primary_form_and_safe_collapsed_tools():
    document = (ROOT / "index.html").read_text(encoding="utf-8")
    elements, structure = Elements(), Structure()
    elements.feed(document)
    structure.feed(document)
    assert not structure.stack
    assert elements.ids["conversation-title"][0] == "h1"
    assert elements.ids["conversation-history"][0] == "details"
    assert "open" not in elements.ids["conversation-history"][1]
    assert elements.ids["composer"][0] == "form"
    assert elements.ids["submit"][1]["type"] == "submit"
    assert "message" in elements.labels
    assert not any(tag == "details" for tag, _, _ in structure.parents["composer"])
    assert any(tag == "details" for tag, _, _ in structure.parents["snapshot-file"])
    assert not any(tag == "details" for tag, _, _ in structure.parents["presence-motion"])
    assert all(anchor[1:] in elements.ids for anchor in structure.anchors)
    assert "Demonstração isolada" in document and "Nenhuma ação real" in document


def test_examples_only_prepare_text_and_never_claim_a_connected_feature():
    structure = Structure()
    structure.feed((ROOT / "index.html").read_text(encoding="utf-8"))
    assert len(structure.prompts) == 2
    for tag, attrs in structure.prompts:
        assert tag == "button" and attrs["type"] == "button"
        assert 0 < len(attrs["data-prompt"]) < 4000
    source = (ROOT / "app.mjs").read_text(encoding="utf-8")
    handler = source.split('document.querySelectorAll("[data-prompt]")', 1)[1].split(
        "function syncNavigation", 1
    )[0]
    assert "button.dataset.prompt" in handler and ".focus()" in handler
    assert "submit" not in handler and "controller." not in handler
    assert 'window.addEventListener("hashchange", syncNavigation)' in source
    assert 'byId("voice-panel").open = true' in source


def test_conversation_expands_for_a_real_local_turn_and_resets_presentation():
    source = (ROOT / "app.mjs").read_text(encoding="utf-8")
    assert "const active = state.messages.length > 2" in source
    assert 'byId("conversation-history").open = active' in source
    assert 'document.querySelector(".suggestions").hidden = active' in source
    style = (ROOT / "styles.css").read_text(encoding="utf-8")
    assert ".conversation[data-active=true]" in style
    assert "@media (max-width: 480px)" in style
    assert "overflow-y: auto" not in style  # One document scroll, not nested panels.
    assert "min-height: 44px" in style
    assert "--muted: #a1b3b7" in style
