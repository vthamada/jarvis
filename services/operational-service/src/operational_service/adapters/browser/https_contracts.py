"""Local, bounded contracts for credentialless HTTPS observations, not grants."""

from __future__ import annotations

import ipaddress
import math
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")
_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_SPECIAL = tuple(ipaddress.IPv4Network(value) for value in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
    "192.88.99.0/24", "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24",
    "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4",
))


class HttpsReadRefused(Exception):
    """Internal control flow containing only a locally enumerated error code."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def validate_pin(value: str) -> str:
    if type(value) is not str or not 7 <= len(value) <= 15:
        raise ValueError("invalid_ipv4_pin")
    try:
        address = ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        raise ValueError("invalid_ipv4_pin") from None
    if (str(address) != value or not address.is_global or address.is_reserved
            or address.is_multicast or any(address in network for network in _SPECIAL)):
        raise ValueError("invalid_ipv4_pin")
    return value


def validate_hostname(value: str) -> str:
    if (type(value) is not str or not value.isascii() or not 1 <= len(value) <= 253
            or len(value.split(".")) < 2
            or not re.search(r"[a-z]", value.rsplit(".", 1)[-1])
            or any(not _LABEL.fullmatch(label) for label in value.split("."))):
        raise ValueError("invalid_https_target")
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    raise ValueError("invalid_https_target")


def validate_target(value: str) -> tuple[str, str]:
    """Canonical ASCII URL: DNS hostname, default 443, path/query, no fragment/auth."""
    if (type(value) is not str or not 1 <= len(value) <= 4096 or not value.isascii()
            or any(ord(char) <= 32 or ord(char) == 127 for char in value)
            or "\\" in value or "#" in value):
        raise ValueError("invalid_https_target")
    try:
        parsed = urlsplit(value)
        host = validate_hostname(parsed.hostname)
        if (parsed.scheme != "https" or parsed.netloc != host or parsed.username is not None
                or parsed.password is not None or parsed.port is not None
                or not parsed.path.startswith("/") or parsed.fragment):
            raise ValueError("invalid_https_target")
        target = parsed.path + ("?" + parsed.query if parsed.query else "")
        if value != f"https://{host}{target}":
            raise ValueError("invalid_https_target")
        # Preserve valid encoded octets exactly; reject malformed/lowercase escapes.
        if re.search(r"%(?![0-9A-F]{2})", target):
            raise ValueError("invalid_https_target")
        if re.search(r"[^A-Za-z0-9._~:/?@!$&'()*+,;=%-]", target):
            raise ValueError("invalid_https_target")
        return host, target
    except (ValueError, TypeError):
        raise ValueError("invalid_https_target") from None


@dataclass(frozen=True, slots=True)
class HttpsReadLimits:
    max_body_bytes: int = 262144
    max_header_bytes: int = 16384
    max_trailer_bytes: int = 8192
    max_chunk_line_bytes: int = 4096
    max_chunks: int = 4096
    max_overhead_bytes: int = 65536
    deadline_seconds: float = 10.0

    def __post_init__(self) -> None:
        for name, lower, upper in (
            ("max_body_bytes", 0, 262144), ("max_header_bytes", 64, 16384),
            ("max_trailer_bytes", 2, 8192), ("max_chunk_line_bytes", 3, 4096),
            ("max_chunks", 1, 4096), ("max_overhead_bytes", 64, 65536),
        ):
            value = getattr(self, name)
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError("invalid_https_limits")
        if (type(self.deadline_seconds) not in (int, float)
                or not math.isfinite(self.deadline_seconds)
                or not 0.05 <= self.deadline_seconds <= 60):
            raise ValueError("invalid_https_limits")


@dataclass(frozen=True, slots=True)
class HttpsReadScope:
    principal_ref: str
    session_ref: str
    scope_ref: str
    purpose_ref: str
    url: str = field(repr=False)
    ipv4_pin: str = field(repr=False)

    def __post_init__(self) -> None:
        for value in (self.principal_ref, self.session_ref, self.scope_ref, self.purpose_ref):
            if type(value) is not str or not _REF.fullmatch(value):
                raise ValueError("invalid_https_reference")
        validate_target(self.url)
        validate_pin(self.ipv4_pin)


@dataclass(frozen=True, slots=True)
class HttpsReadRequest:
    principal_ref: str
    session_ref: str
    scope_ref: str
    purpose_ref: str
    url: str = field(repr=False)
    ipv4_pin: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class HttpsObservation:
    status: str
    error_code: str | None
    text: str | None = field(default=None, repr=False)
    source_url: str | None = field(default=None, repr=False)
    observed_at: str | None = None
    content_sha256: str | None = field(default=None, repr=False)
    byte_count: int = 0
    media_type: str | None = None
    mode: str = "credentialless_https_observation"
    authority: str = "none"
    untrusted_data: bool = True

    def telemetry(self) -> dict[str, str | int | bool | None]:
        return {
            "event_name": "isolated_https_observation", "status": self.status,
            "error_code": self.error_code, "byte_count": self.byte_count,
            "mode": self.mode, "authority": self.authority,
            "untrusted_data": self.untrusted_data,
        }
