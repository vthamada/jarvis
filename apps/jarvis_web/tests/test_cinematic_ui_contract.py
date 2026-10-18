"""Static cinematic UI contracts, independent from browser rendering and JS state.

These checks cover semantic DOM, safe initial controls and asset boundaries.
They do not establish viewport quality, audio playback or runtime animation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

import pytest

from apps.jarvis_api.local_server import ASSET_ROOT as LIVE_ROOT
from apps.jarvis_api.local_server import ASSETS as LIVE_ASSETS
from apps.jarvis_api.local_server import CSP as LIVE_CSP
from apps.jarvis_web.serve import ASSET_ROOT as FIXTURE_ROOT
from apps.jarvis_web.serve import ASSETS as FIXTURE_ASSETS
from apps.jarvis_web.serve import CSP as FIXTURE_CSP

ROOT = Path(__file__).resolve().parents[1]
VOID_TAGS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
     "param", "source", "track", "wbr"}
)


@dataclass
class Node:
    tag: str
    attrs: dict[str, str | None]
    ancestors: tuple[Node, ...]
    text_parts: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(" ".join(self.text_parts).split())

    @property
    def classes(self) -> set[str]:
        return set((self.attrs.get("class") or "").split())


class Document(HTMLParser):
    """Validate authored nesting and resolve actual labels and ARIA targets."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.nodes: list[Node] = []
        self.ids: dict[str, Node] = {}
        self.stack: list[Node] = []
        self.feed(source)
        self.close()
        assert not self.stack, "The document has unclosed elements"

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        assert len(values) == len(attrs), f"Duplicate attributes on {tag}"
        node = Node(tag, values, tuple(self.stack))
        self.nodes.append(node)
        if identifier := values.get("id"):
            assert identifier not in self.ids, f"Duplicate id: {identifier}"
            self.ids[identifier] = node
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        assert self.stack, f"Unexpected closing element: {tag}"
        assert self.stack[-1].tag == tag, f"Invalid nesting before closing {tag}"
        self.stack.pop()

    def handle_data(self, data):
        for node in self.stack:
            node.text_parts.append(data)

    def with_class(self, name: str) -> list[Node]:
        return [node for node in self.nodes if name in node.classes]

    def labels_for(self, identifier: str) -> list[Node]:
        return [node for node in self.nodes
                if node.tag == "label" and node.attrs.get("for") == identifier]


def document(filename: str) -> Document:
    return Document((ROOT / filename).read_text(encoding="utf-8"))


@pytest.mark.parametrize("filename,legacy_style", [
    ("index.html", "/styles.css"),
    ("live-index.html", "/live-style.css"),
])
def test_cinematic_theme_is_shared_and_keeps_semantic_document(filename, legacy_style):
    page = document(filename)
    bodies = [node for node in page.nodes if node.tag == "body"]
    assert len(bodies) == 1
    assert "cinematic-interface" in bodies[0].classes
    styles = [node.attrs.get("href") for node in page.nodes
              if node.tag == "link" and node.attrs.get("rel") == "stylesheet"]
    assert styles.count("/cinematic.css") == 1
    assert styles.index("/cinematic.css") > styles.index(legacy_style)
    stages = page.with_class("cinematic-stage")
    assert len(stages) == 1
    assert page.with_class("holo-core")
    assert sum(stages[0] in node.ancestors for node in page.with_class("holo-panel")) >= 4
    assert page.with_class("holo-stack")
    assert any(node.tag == "main" for node in page.nodes)
    assert any(node.tag == "h1" and node.text for node in page.nodes)


def test_fixture_composition_has_masthead_and_primary_request_before_technical_deck():
    page = document("index.html")
    mastheads = page.with_class("cinematic-masthead")
    assert len(mastheads) == 1 and mastheads[0].tag == "header"
    assert "JARVIS" in mastheads[0].text
    stage = page.with_class("cinematic-stage")[0]
    core = page.with_class("holo-core")[0]
    deck = page.ids["fixture-technical-deck"]
    composer = page.ids["composer"]
    assert page.nodes.index(mastheads[0]) < page.nodes.index(stage)
    stage_children = [node for node in page.nodes
                      if node.ancestors and node.ancestors[-1] is stage]
    assert stage_children[0] is core
    assert page.nodes.index(stage) < page.nodes.index(composer) < page.nodes.index(deck)
    assert not any(node.tag == "details" for node in composer.ancestors)
    for identifier in (
        "conversation-history", "conversation-pack-panel", "snapshot-file",
        "presence-audio-panel", "voice-panel", "transcript-panel",
    ):
        assert page.nodes.index(composer) < page.nodes.index(page.ids[identifier])
    assert deck in page.ids["snapshot-file"].ancestors
    assert deck in page.ids["approvals"].ancestors
    assert all(deck in node.ancestors for node in page.nodes if node.tag == "nav")
    assert page.ids["presence-audio-open"].attrs.get("type") == "button"
    assert page.ids["submit"].attrs.get("type") == "submit"


def test_fixture_stage_has_brief_context_agenda_activity_without_fictitious_calendar():
    page = document("index.html")
    stage = page.with_class("cinematic-stage")[0]
    left = page.with_class("holo-left")[0]
    right = page.with_class("holo-right")[0]
    assert left in page.ids["objective"].ancestors
    assert left in page.ids["artifacts"].ancestors
    assert right in page.ids["activity"].ancestors
    agenda = page.ids["fixture-agenda"]
    assert stage in agenda.ancestors and right in agenda.ancestors
    assert "holo-panel" in agenda.classes
    assert "Briefing" in page.ids["objective"].text
    assert "Contexto" in page.ids["artifacts"].text
    assert "Agenda" in agenda.text and "Nenhum calendário conectado" in agenda.text
    assert not any(node.tag == "time" and agenda in node.ancestors for node in page.nodes)
    assert "reunião" not in agenda.text.casefold()
    assert page.ids["steps"].tag == "ol"
    assert page.ids["activity-list"].tag == "ul"


def test_fixture_primary_notice_stays_visible_outside_collapsed_technical_controls():
    page = document("index.html")
    banners = page.with_class("mode-banner")
    assert len(banners) == 1
    banner = banners[0]
    assert "Demonstração isolada" in banner.text and "Nenhuma ação real" in banner.text
    assert "hidden" not in banner.attrs
    assert not any(node.tag == "details" or "hidden" in node.attrs for node in banner.ancestors)
    assert page.nodes.index(banner) < page.nodes.index(page.with_class("cinematic-stage")[0])


@pytest.mark.parametrize("filename", ["index.html", "live-index.html"])
def test_cinematic_labels_landmarks_and_aria_references_resolve(filename):
    page = document(filename)
    for node in page.nodes:
        for reference in ("aria-labelledby", "aria-describedby"):
            for target in (node.attrs.get(reference) or "").split():
                assert target in page.ids, f"Missing {reference} target: {target}"
                if reference == "aria-labelledby":
                    assert page.ids[target].text, f"Empty label target: {target}"
        if node.tag == "label" and (target := node.attrs.get("for")):
            assert target in page.ids, f"Label has no control: {target}"
            assert page.ids[target].tag in {"input", "textarea", "select", "button"}
        if node.tag == "a" and (href := node.attrs.get("href") or "").startswith("#"):
            assert href[1:] in page.ids, f"Missing in-page destination: {href}"
        if node.tag in {"input", "textarea", "select"}:
            identifier = node.attrs.get("id") or ""
            assert node.attrs.get("aria-label") or page.labels_for(identifier), (
                f"Control has no accessible label: {identifier}"
            )
        assert not any(name.startswith("on") for name in node.attrs)
        if node.tag == "script":
            assert node.attrs.get("type") == "module"
            assert (node.attrs.get("src") or "").startswith("/")
            assert not node.text, "Executable script must remain in same-origin modules"


@pytest.mark.parametrize("filename,canvas_id,motion_id", [
    ("index.html", "particle-sphere", "presence-motion"),
    ("live-index.html", "live-particle-sphere", "live-motion"),
])
def test_cinematic_canvas_is_decorative_and_motion_control_is_explicit(
    filename, canvas_id, motion_id
):
    page = document(filename)
    canvas = page.ids[canvas_id]
    assert canvas.tag == "canvas" and canvas.attrs.get("aria-hidden") == "true"
    assert "tabindex" not in canvas.attrs
    button = page.ids[motion_id]
    assert button.tag == "button" and button.attrs.get("type") == "button"
    assert button.attrs.get("aria-pressed") == "false"
    assert button.text
    assert not any(node.tag == "details" for node in button.ancestors)


def test_live_local_audio_has_accessible_manual_controls_and_safe_initial_state():
    page = document("live-index.html")
    panel = page.ids["live-audio-panel"]
    assert panel.tag == "details" and "open" not in panel.attrs
    audio_input = page.ids["live-audio-file"]
    assert audio_input.tag == "input" and audio_input.attrs.get("type") == "file"
    assert page.labels_for("live-audio-file")
    assert {".wav", "audio/wav"} <= set((audio_input.attrs.get("accept") or "").split(","))
    assert "multiple" not in audio_input.attrs and "capture" not in audio_input.attrs
    assert "live-audio-help" in (audio_input.attrs.get("aria-describedby") or "").split()
    for name in ("live-audio-play", "live-audio-stop", "live-audio-clear"):
        button = page.ids[name]
        assert button.tag == "button" and button.attrs.get("type") == "button"
        assert "disabled" in button.attrs
        assert button.text
        assert panel in button.ancestors
    help_text = page.ids["live-audio-help"].text.casefold()
    assert "sem microfone" in help_text
    assert "upload" in help_text and "core" in help_text
    assert "autom" in help_text and "clique" in help_text
    notice = page.ids["live-audio-notice"]
    assert notice.attrs.get("aria-live") == "polite" and notice.text
    notes = page.with_class("dock-audio-note")
    assert len(notes) == 1
    assert "manual" in notes[0].text.casefold() and "sem microfone" in notes[0].text.casefold()
    assert not any(node.tag == "details" for node in notes[0].ancestors)
    assert not any("autoplay" in node.attrs for node in page.nodes)


def test_live_redesign_preserves_pairing_consent_and_integral_canonical_output():
    page = document("live-index.html")
    assert page.ids["live-shell"].attrs.get("data-paired") == "false"
    assert page.ids["live-pair-form"].tag == "form"
    assert page.ids["live-secret"].attrs.get("type") == "password"
    assert page.ids["live-form"].tag == "form"
    for name in ("live-query", "live-send", "live-stop", "live-recover"):
        assert "disabled" in page.ids[name].attrs
    consent = page.ids["live-generative-consent"]
    assert consent.attrs.get("type") == "checkbox"
    assert "checked" not in consent.attrs and "disabled" in consent.attrs
    assert "hidden" in page.ids["live-result"].attrs
    assert "hidden" in page.ids["live-projection"].attrs
    assert page.ids["live-final"].tag == "pre"
    assert page.ids["live-canonical-details"].tag == "details"
    assert page.ids["live-canonical-details"] in page.ids["live-final"].ancestors
    assert "sem alterações" in page.ids["live-canonical-summary"].text.casefold()
    fixture = document("index.html")
    assert "Demonstração isolada" in next(node.text for node in fixture.nodes if node.tag == "body")
    assert "Nenhuma ação real" in next(node.text for node in fixture.nodes if node.tag == "body")


@pytest.mark.parametrize("assets,asset_root,expected", [
    (FIXTURE_ASSETS, FIXTURE_ROOT, {"/cinematic.css": "text/css; charset=utf-8"}),
    (LIVE_ASSETS, LIVE_ROOT, {
        "/cinematic.css": "text/css; charset=utf-8",
        "/live-presence.mjs": "text/javascript; charset=utf-8",
        "/local-voice-playback.mjs": "text/javascript; charset=utf-8",
    }),
])
def test_cinematic_assets_exist_in_real_allowlists_with_strict_mime(assets, asset_root, expected):
    for route, mime in expected.items():
        assert assets[route] == (route[1:], mime)
        path = asset_root / route[1:]
        assert path.is_file() and not path.is_symlink()
        assert path.read_bytes(), f"Empty asset: {route}"
    assert "/live-presence.mjs" not in FIXTURE_ASSETS
    assert not any("upload" in route or "audio" in route for route in assets)


def test_cinematic_design_does_not_relax_existing_content_security_policies():
    assert FIXTURE_CSP == (
        "default-src 'none'; script-src 'self'; style-src 'self'; "
        "connect-src 'none'; img-src 'none'; font-src 'none'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )
    assert LIVE_CSP == (
        "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; "
        "img-src 'none'; font-src 'none'; media-src 'none'; worker-src 'none'; "
        "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
    )


def test_cinematic_styles_preserve_focus_motion_preferences_and_local_assets():
    source = (ROOT / "cinematic.css").read_text(encoding="utf-8")
    style = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL).casefold()
    assert "prefers-reduced-motion" in style
    assert "forced-colors" in style
    assert ":focus-visible" in style and "outline" in style
    assert re.search(r"@media\s*\([^)]*max-width\s*:", style)
    assert re.search(r"\bmin-width\s*:\s*0(?:\D|$)", style)
    assert "overflow-wrap" in style
    assert "@import" not in style and "@font-face" not in style
    assert not re.search(r"\burl\s*\(", style), "No external or embedded graphic dependency"
    for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", style):
        if re.search(r"\bposition\s*:\s*fixed\b", declarations):
            assert "::before" in selectors or "::after" in selectors, (
                "Interactive panels must stay in document flow, not viewport overlays"
            )
            assert re.search(r"\bpointer-events\s*:\s*none\b", declarations)
        if re.search(r"(?:^|,)\s*(?:html|body|\.cinematic-interface)\s*(?:,|$)", selectors):
            assert not re.search(r"\boverflow(?:-y)?\s*:\s*(?:hidden|clip)\b", declarations), (
                "The document must remain vertically scrollable at zoom and narrow widths"
            )
