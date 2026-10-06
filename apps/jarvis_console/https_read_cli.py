"""Explicit credentialless HTTPS observation; no Core/store or capability promotion."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path

from apps.jarvis_console.bootstrap import ROOT, ensure_src_paths
from apps.jarvis_console.review_input import _requires_redaction, read_review_input
from apps.jarvis_console.runtime import ConsoleRuntime

MAX_RESULT_BYTES = 1_048_576
_BINDING_FIELDS = {"principal_ref", "session_ref", "scope_ref", "purpose_ref", "url", "ipv4_pin"}
_LIMIT_FIELDS = {
    "max_body_bytes", "max_header_bytes", "max_trailer_bytes", "max_chunk_line_bytes",
    "max_chunks", "max_overhead_bytes", "deadline_seconds",
}


def _validate_observation(result, scope, limits):
    try:
        _inspect_observation(result, scope, limits)
    except Exception:
        raise ValueError("invalid_https_observation") from None


def _inspect_observation(result, scope, limits):
    from operational_service.adapters.browser.https_contracts import HttpsObservation
    from operational_service.adapters.browser.https_reader import _ERROR_CODES

    if (type(result) is not HttpsObservation or result.authority != "none"
            or result.untrusted_data is not True
            or result.mode != "credentialless_https_observation"
            or type(result.byte_count) is not int
            or not 0 <= result.byte_count <= limits.max_body_bytes):
        raise ValueError("invalid_https_observation")
    if result.status == "observed":
        if (result.error_code is not None or type(result.text) is not str
                or len(result.text) > limits.max_body_bytes
                or result.source_url != scope.url
                or result.media_type not in {"text/plain", "text/html"}
                or type(result.observed_at) is not str):
            raise ValueError("invalid_https_observation")
        raw = result.text.encode("utf-8", errors="strict")
        stamp = datetime.fromisoformat(result.observed_at)
        if (len(raw) != result.byte_count
                or result.content_sha256 != hashlib.sha256(raw).hexdigest()
                or stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0
                or any((ord(c) < 32 and c not in "\r\n\t") or ord(c) == 127 for c in result.text)):
            raise ValueError("invalid_https_observation")
    elif result.status in {"refused", "cancelled"}:
        codes = _ERROR_CODES | {"authorization_required", "invalid_cancellation",
                                "scope_mismatch", "reader_busy"}
        if (result.error_code not in codes or result.byte_count != 0
                or (result.status == "cancelled") != (result.error_code == "cancelled")
                or any(value is not None for value in (result.text, result.source_url,
                    result.observed_at, result.content_sha256, result.media_type))):
            raise ValueError("invalid_https_observation")
    else:
        raise ValueError("invalid_https_observation")


def observe_document(document: dict, *, authorized: bool = False, include_content: bool = False):
    """Input labels are declared bindings, not authenticated identity or grants."""
    if authorized is not True:
        raise ValueError("authorization_required")
    if type(include_content) is not bool:
        raise ValueError("invalid_https_read_input")
    if (type(document) is not dict or set(document) not in (
            {"scope", "request"}, {"scope", "request", "limits"})):
        raise ValueError("invalid_https_read_input")
    for name in ("scope", "request"):
        if type(document[name]) is not dict or set(document[name]) != _BINDING_FIELDS:
            raise ValueError("invalid_https_read_input")
    options = document.get("limits", {})
    if type(options) is not dict or not set(options) <= _LIMIT_FIELDS:
        raise ValueError("invalid_https_read_input")
    ensure_src_paths()
    from operational_service.adapters.browser.https_contracts import (
        HttpsReadLimits,
        HttpsReadRequest,
        HttpsReadScope,
    )
    from operational_service.adapters.browser.https_reader import CredentiallessHttpsReader

    scope = HttpsReadScope(**document["scope"])
    limits = HttpsReadLimits(**options)
    request = HttpsReadRequest(**document["request"])
    result = CredentiallessHttpsReader(scope, limits).observe(request, authorized=True)
    _validate_observation(result, scope, limits)
    payload = result.telemetry() | {
        "operator_authenticated": False, "runtime_capability_promoted": False,
        "content_included": False, "content_withheld": False,
    }
    if include_content and result.status == "observed":
        content = {
            "text": result.text, "source_url": result.source_url,
            "observed_at": result.observed_at, "content_sha256": result.content_sha256,
            "media_type": result.media_type,
        }
        redactor = ConsoleRuntime(
            output_format="json", sensitive_paths=(str(ROOT), str(Path.home())),
        )
        if _requires_redaction(content, redactor):
            # Never alter exact text while preserving its original digest/provenance.
            payload["content_withheld"] = True
        else:
            payload["content"] = content
            payload["content_included"] = True
    encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True)
    if len(encoded.encode("ascii")) > MAX_RESULT_BYTES:
        raise ValueError("invalid_https_read_output")
    return payload


class _SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's usual error contains raw argv, including private values.
        raise ValueError("invalid_https_read_options")


def main(argv=None) -> int:
    parser = _SafeParser(description=__doc__)
    parser.add_argument("--authorized", action="store_true", required=True)
    parser.add_argument("--include-content", action="store_true")
    try:
        args = parser.parse_args(argv)
        document = read_review_input()
        payload = observe_document(document, authorized=args.authorized,
                                   include_content=args.include_content)
        print(json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True))
        return 0 if payload["status"] == "observed" else 3
    except KeyboardInterrupt:
        print('{"status":"cancelled","error_code":"cancelled","authority":"none"}')
        return 3
    except Exception:
        print('{"status":"refused","error_code":"invalid_https_read_input","authority":"none"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
