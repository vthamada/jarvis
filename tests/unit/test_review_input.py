import io
import json
from argparse import Namespace

import pytest

from apps.jarvis_console import review_input
from apps.jarvis_console.runtime import ConsoleCommandError


def stdin_bytes(monkeypatch, raw):
    monkeypatch.setattr(review_input.sys, "stdin", io.TextIOWrapper(io.BytesIO(raw)))


@pytest.mark.parametrize("raw", [
    b"", b"[]", b"null", b"{", b'\xef\xbb\xbf{}', b'{"x":"\xff"}',
    b'{"x":1,"x":2}', b'{"x":1,"\\u0078":2}',
    b'{"items":[{"x":1,"x":2}]}', b'{"n":NaN}', b'{"n":Infinity}',
    b'{"n":-Infinity}', b'{"n":1e999}', b'{"x":"\\ud800"}',
    b'{"x":' + b'[' * 20 + b'0' + b']' * 20 + b'}',
    b'{"x":' + b'[' * 2000 + b'0' + b']' * 2000 + b'}',
    b' ' * (review_input.MAX_INPUT_BYTES + 1),
], ids=[f"invalid-{index}" for index in range(17)])
def test_stdin_invalid_never_returns_partial(monkeypatch, raw):
    stdin_bytes(monkeypatch, raw)
    with pytest.raises((ValueError, RecursionError)):
        review_input.read_review_input()


def test_stdin_unicode_and_exact_bytes_boundary(monkeypatch):
    raw = json.dumps({"x": "café 🧠"}, ensure_ascii=False).encode()
    stdin_bytes(monkeypatch, raw + b' ' * (review_input.MAX_INPUT_BYTES - len(raw)))
    assert review_input.read_review_input() == {"x": "café 🧠"}


def test_stdin_text_adapter_checks_utf8_bytes(monkeypatch):
    monkeypatch.setattr(review_input.sys, "stdin", io.StringIO('{"x":"' + 'é' * 40000 + '"}'))
    with pytest.raises(ValueError):
        review_input.read_review_input()


def test_read_request_is_bounded(monkeypatch):
    class Binary:
        def read(self, size):
            assert size == review_input.MAX_INPUT_BYTES + 1
            return b'{}'

    class Pipe:
        buffer = Binary()

        def isatty(self):
            return False

    monkeypatch.setattr(review_input.sys, "stdin", Pipe())
    assert review_input.read_review_input() == {}


def test_interactive_refused_before_read(monkeypatch):
    class Terminal:
        def isatty(self):
            return True

        def read(self, *args):
            pytest.fail("interactive read")

    monkeypatch.setattr(review_input.sys, "stdin", Terminal())
    with pytest.raises(ValueError):
        review_input.read_review_input()


@pytest.mark.parametrize("raw", [b'{"private-marker":', b'{"x":1,"x":2}', b'[]'])
def test_command_exception_is_fixed_and_no_builder_call(monkeypatch, raw):
    stdin_bytes(monkeypatch, raw)
    with pytest.raises(ConsoleCommandError) as caught:
        review_input.run_review_product(
            Namespace(include_content=True), lambda *a, **k: pytest.fail("builder called"),
        )
    assert caught.value.error_code == "review_input_refused"
    assert int(caught.value.exit_code) == 2
    assert "private-marker" not in str(caught.value)


@pytest.mark.parametrize("sensitive", [
    "password=private-marker", "Bearer private-marker", "C:\\Users\\Secret\\file.txt",
    "/home/person/private-marker", "sk-" + "x" * 32,
    "Authorization: Basic private-marker", "https://name:private-marker@example.test/",
    "-----BEGIN PRIVATE KEY-----private-marker-----END PRIVATE KEY-----",
])
def test_sensitive_content_wholly_withheld_not_rewritten(monkeypatch, sensitive):
    stdin_bytes(monkeypatch, b'{}')
    calls = []

    def builder(document, *, include_content):
        calls.append(include_content)
        result = {"status": "reviewable", "digest": "a" * 64}
        if include_content:
            result["content"] = {"quote": sensitive}
        return result

    result = review_input.run_review_product(Namespace(include_content=True), builder)
    output = json.loads(result.outputs[0])
    assert calls == [True, False]
    assert "content" not in output
    assert output["content_withheld"] is True
    assert output["content_withheld_reason"] == "sensitive_display_content"
    assert "private-marker" not in result.outputs[0]
    assert "<redacted>" not in result.outputs[0]
    assert output["digest"] == "a" * 64


def test_untrusted_markup_and_terminal_controls_remain_escaped_data(monkeypatch):
    stdin_bytes(monkeypatch, b'{}')
    quote = '<script>alert(1)</script>\x1b[31m\u202e\n'
    result = review_input.run_review_product(
        Namespace(include_content=True), lambda *a, **k: {"content": {"quote": quote}},
    )
    assert "\x1b" not in result.outputs[0] and "\u202e" not in result.outputs[0]
    assert json.loads(result.outputs[0])["content"]["quote"] == quote


def test_builder_error_never_exposed(monkeypatch):
    stdin_bytes(monkeypatch, b'{}')

    def builder(*args, **kwargs):
        raise RuntimeError("unclassified-private-marker")

    with pytest.raises(ConsoleCommandError) as caught:
        review_input.run_review_product(Namespace(include_content=False), builder)
    assert "private-marker" not in str(caught.value)


@pytest.mark.parametrize("payload", [
    {"value": "secret=private-marker"}, {"value": float("nan")},
    {"value": "x" * (review_input.MAX_OUTPUT_BYTES + 1)},
], ids=["private-metadata", "nonfinite", "oversized-output"])
def test_invalid_builder_output_is_not_published(monkeypatch, payload):
    stdin_bytes(monkeypatch, b'{}')
    with pytest.raises(ConsoleCommandError):
        review_input.run_review_product(
            Namespace(include_content=False), lambda *a, **k: payload,
        )
