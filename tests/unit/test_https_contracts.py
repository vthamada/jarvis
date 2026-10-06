"""Pure scope/pin/limit validation, including version-independent IPv4 exclusions."""

from __future__ import annotations

import pytest
from operational_service.adapters.browser.https_contracts import (
    HttpsReadLimits,
    HttpsReadScope,
    validate_hostname,
    validate_pin,
    validate_target,
)


@pytest.mark.parametrize("pin", [
    "0.0.0.0", "10.0.0.1", "100.64.0.1", "100.127.255.254", "127.0.0.1",
    "169.254.169.254", "172.16.0.1", "172.31.255.254", "192.168.0.1", "192.0.0.8",
    "192.0.0.9", "192.0.2.1", "192.88.99.1", "198.18.0.1", "198.19.255.254",
    "198.51.100.1", "203.0.113.1", "224.0.0.1", "239.255.255.254", "240.0.0.1",
    "255.255.255.255", "::1", "::ffff:8.8.8.8", "8.8.8.8:443", "8.008.8.8",
    "0x08080808", "134744072", "8.8.8", "8.8.8.8 ", " 8.8.8.8", "dns.example",
    "1" * 10000, None, True, 134744072,
])
def test_non_public_non_canonical_pin_is_rejected(pin):
    with pytest.raises(ValueError, match="invalid_ipv4_pin"):
        validate_pin(pin)


@pytest.mark.parametrize("pin", ["8.8.8.8", "1.1.1.1", "9.9.9.9"])
def test_public_literal_pin_preserved(pin):
    assert validate_pin(pin) == pin


@pytest.mark.parametrize("url", [
    "https://example.test/", "https://example.test/a/b.html?lang=pt&item=one",
    "https://xn--exmple-cua.test/%C3%A1?item=one%20two", "https://example.test/a%2Fb",
])
def test_canonical_ascii_path_and_query_preserved_without_dns(url):
    host, target = validate_target(url)
    assert url == f"https://{host}{target}"


@pytest.mark.parametrize("url", [
    "http://example.test/", "HTTPS://example.test/", "https://Example.test/",
    "https://example.test", "https://example.test:443/", "https://example.test:8443/",
    "https://user:private@example.test/", "https://private@example.test/",
    "https://example.test/#fragment", "https://example.test/?", "https://example.test./",
    "https://example.test/a b", "https://example.test/\\private", "https://example.test/%0a",
    "https://example.test/%", "https://example.test/%GG", "https://example.test/á",
    "https://example.test/\r\nAuthorization:private", "https://8.8.8.8/",
    "https://010.001.1.1/", "https://localhost/", "https://a..test/", "https://-a.test/",
    "https://example.test/" + "x" * 4096, None, True, [],
])
def test_invalid_targets_are_refused_with_fixed_error(url):
    with pytest.raises(ValueError) as error:
        validate_target(url)
    assert str(error.value) == "invalid_https_target"


@pytest.mark.parametrize("host", ["private", "8.8.8.8", "010.001.1.1", "a.123", "A.test"])
def test_hostname_not_ip_or_ambiguous_form(host):
    with pytest.raises(ValueError, match="invalid_https_target"):
        validate_hostname(host)


@pytest.mark.parametrize("field,upper", [
    ("max_body_bytes", 262144), ("max_header_bytes", 16384),
    ("max_trailer_bytes", 8192), ("max_chunk_line_bytes", 4096),
    ("max_chunks", 4096), ("max_overhead_bytes", 65536),
])
def test_limit_ceilings_cannot_expand_or_accept_boolean(field, upper):
    assert getattr(HttpsReadLimits(**{field: upper}), field) == upper
    for value in (upper + 1, -1, True, 1.5, "private"):
        with pytest.raises(ValueError, match="invalid_https_limits"):
            HttpsReadLimits(**{field: value})


@pytest.mark.parametrize("deadline", [False, 0, -1, 60.001, float("nan"), float("inf"), "10"])
def test_deadline_finite_numeric_and_bounded(deadline):
    with pytest.raises(ValueError, match="invalid_https_limits"):
        HttpsReadLimits(deadline_seconds=deadline)


def test_scope_repr_does_not_include_target_or_pin():
    scope = HttpsReadScope("operator:a", "session:a", "scope:a", "purpose:read",
                           "https://example.test/private/path", "8.8.8.8")
    assert scope.url not in repr(scope) and scope.ipv4_pin not in repr(scope)
