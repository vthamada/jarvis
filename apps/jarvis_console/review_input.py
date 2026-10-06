"""Bounded stdin review products; no Core, paths, network or effect authority."""

from __future__ import annotations

import json
import math
import sys
from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

from apps.jarvis_console.bootstrap import ROOT
from apps.jarvis_console.registry import CommandExecutionResult
from apps.jarvis_console.runtime import ConsoleCommandError, ConsoleExitCode, ConsoleRuntime

MAX_INPUT_BYTES = 65_536
MAX_OUTPUT_BYTES = 262_144
MAX_DEPTH = 12


def _invalid() -> None:
    raise ValueError("invalid_review_input")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _depth(value: object, level: int = 0) -> None:
    if level > MAX_DEPTH:
        _invalid()
    if type(value) is dict:
        for key, child in value.items():
            _depth(key, level + 1)
            _depth(child, level + 1)
    elif type(value) is list:
        for child in value:
            _depth(child, level + 1)
    elif type(value) is str:
        # Reject ill-formed Unicode before any hash/UTF-8 encoding or display.
        value.encode("utf-8", errors="strict")
    elif type(value) is float and not math.isfinite(value):
        _invalid()


def read_review_input() -> dict:
    """Read a finite UTF-8 document only from an explicit stdin pipe ending EOF.

    A pipe must close; byte bounds are not a deadline for an arbitrary producer.
    Interactive terminals are refused before a read. No filenames are accepted.
    """
    if sys.stdin.isatty():
        _invalid()
    binary = getattr(sys.stdin, "buffer", None)
    if binary is not None:
        raw = binary.read(MAX_INPUT_BYTES + 1)
        if type(raw) is not bytes or not 1 <= len(raw) <= MAX_INPUT_BYTES:
            _invalid()
        source = raw.decode("utf-8", errors="strict")
    else:
        source = sys.stdin.read(MAX_INPUT_BYTES + 1)
        if type(source) is not str or not 1 <= len(source.encode("utf-8")) <= MAX_INPUT_BYTES:
            _invalid()
    document = json.loads(
        source, object_pairs_hook=_unique_object,
        parse_constant=lambda _: _invalid(),
    )
    if type(document) is not dict:
        _invalid()
    _depth(document)
    return document


def _requires_redaction(value: object, redactor: ConsoleRuntime) -> bool:
    if type(value) is str:
        return (redactor.redact(value)[1]
                or redactor.redact(json.dumps(value, ensure_ascii=True))[1])
    if type(value) is dict:
        return any(_requires_redaction(key, redactor) or _requires_redaction(child, redactor)
                   for key, child in value.items())
    if type(value) is list:
        return any(_requires_redaction(child, redactor) for child in value)
    return False


def run_review_product(
    args: Namespace, builder: Callable[..., dict],
) -> CommandExecutionResult:
    """Never redact an exact quote/diff in place while retaining its fingerprints."""
    try:
        document = read_review_input()
        include_content = args.include_content is True
        payload = builder(document, include_content=include_content)
        redactor = ConsoleRuntime(
            output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
        )
        withheld = include_content and _requires_redaction(payload, redactor)
        if withheld:
            payload = builder(document, include_content=False)
        payload = dict(payload)
        payload["content_withheld"] = bool(withheld)
        payload["content_withheld_reason"] = "sensitive_display_content" if withheld else None
        _depth(payload)
        encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True)
        if (len(encoded.encode("ascii")) > MAX_OUTPUT_BYTES
                or redactor.redact(encoded)[1]):
            _invalid()
        # Text format is still escaped JSON; untrusted data is never terminal markup.
        return CommandExecutionResult(outputs=[encoded])
    except Exception:
        # Do not echo stdin, argv, file content, JSON parser details or exceptions.
        raise ConsoleCommandError(
            "Review input refused; supply a bounded valid UTF-8 JSON document on stdin.",
            error_code="review_input_refused", exit_code=ConsoleExitCode.USAGE_ERROR,
        ) from None
