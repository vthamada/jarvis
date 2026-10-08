"""Synthetic unit coverage of the one-launch pairing boundary."""

import math
import re
from concurrent.futures import ThreadPoolExecutor

import pytest

from apps.jarvis_api.contracts import LocalWebRejected, SessionIdentity
from apps.jarvis_api.local_auth import MAX_PAIRING_ATTEMPTS, LocalAuth


class Clock:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        return self.value


@pytest.fixture
def auth():
    clock = Clock()
    return LocalAuth(clock=clock), clock


def test_minted_tokens_identity_and_exact_session_payload(auth):
    service, _ = auth
    token, csrf, identity = service.pair(service.pairing_secret)
    assert token != csrf != service.pairing_secret
    assert re.fullmatch(r"[0-9a-f]{64}", token)
    assert re.fullmatch(r"[0-9a-f]{64}", csrf)
    assert type(identity) is SessionIdentity
    assert identity.session_ref.startswith("session://web-live/")
    assert identity.principal_ref.startswith("operator://web-live/")
    assert identity.canonical_user_ref.startswith("user://web-live/")
    assert service.authenticate(token) is identity
    assert service.csrf(token, csrf) is identity
    payload = service.session_payload(token, None)
    assert payload == {
        "schema_version": "jarvis-local-session-v1",
        "authenticated": True,
        "session_ref": identity.session_ref,
        "csrf_token": csrf,
        "expires_in_seconds": 900,
        "last_ticket": None,
    }
    assert token not in str(payload)
    assert service.pairing_secret not in str(payload)
    assert "principal_ref" not in payload and "canonical_user_ref" not in payload


@pytest.mark.parametrize(
    "invalid",
    [None, True, 1, [], {}, "", " ", "A" * 64, "0" * 63, "0" * 65, "é" * 64, "0" * 64 + "\n"],
)
def test_pairing_malformed_no_session(auth, invalid):
    service, _ = auth
    with pytest.raises(LocalWebRejected, match="^pairing_refused$"):
        service.pair(invalid)
    with pytest.raises(LocalWebRejected, match="^session_refused$"):
        service.authenticate("0" * 64)


def test_wrong_secret_consumes_bounded_budget(auth):
    service, _ = auth
    wrong = "f" * 64 if service.pairing_secret != "f" * 64 else "e" * 64
    for _ in range(MAX_PAIRING_ATTEMPTS):
        with pytest.raises(LocalWebRejected, match="^pairing_refused$"):
            service.pair(wrong)
    with pytest.raises(LocalWebRejected, match="^pairing_rate_limited$"):
        service.pair(service.pairing_secret)


@pytest.mark.parametrize(
    "elapsed,allowed", [(0, True), (119.999, True), (120, False), (121, False)]
)
def test_pairing_deadline(auth, elapsed, allowed):
    service, clock = auth
    clock.value += elapsed
    if allowed:
        service.pair(service.pairing_secret)
    else:
        with pytest.raises(LocalWebRejected, match="^pairing_unavailable$"):
            service.pair(service.pairing_secret)


@pytest.mark.parametrize(
    "elapsed,remaining", [(0, 900), (0.1, 900), (1, 899), (899, 1), (899.99, 1)]
)
def test_cookie_remaining_integer_ceiling(auth, elapsed, remaining):
    service, clock = auth
    token, _, _ = service.pair(service.pairing_secret)
    clock.value += elapsed
    assert service.session_payload(token, None)["expires_in_seconds"] == remaining


@pytest.mark.parametrize("method", ["authenticate", "csrf", "session_payload"])
def test_expiry_is_fail_closed_and_no_repair(auth, method):
    service, clock = auth
    token, csrf, _ = service.pair(service.pairing_secret)
    clock.value += 900
    args = (
        (token, csrf)
        if method == "csrf"
        else ((token, None) if method == "session_payload" else (token,))
    )
    with pytest.raises(LocalWebRejected, match="^session_refused$"):
        getattr(service, method)(*args)
    with pytest.raises(LocalWebRejected, match="^pairing_unavailable$"):
        service.pair(service.pairing_secret)


@pytest.mark.parametrize(
    "invalid", [None, True, 7, [], {}, "", "x" * 64, "0" * 64, "0" * 63, "0" * 65, "0" * 64 + "\n"]
)
def test_unknown_session_never_authenticates(auth, invalid):
    service, _ = auth
    service.pair(service.pairing_secret)
    with pytest.raises(LocalWebRejected, match="^session_refused$"):
        service.authenticate(invalid)


@pytest.mark.parametrize(
    "invalid", [None, True, 7, [], {}, "", "x" * 64, "0" * 64, "0" * 63, "0" * 65, "0" * 64 + "\n"]
)
def test_csrf_requires_exact_token(auth, invalid):
    service, _ = auth
    token, _, _ = service.pair(service.pairing_secret)
    with pytest.raises(LocalWebRejected, match="^csrf_refused$"):
        service.csrf(token, invalid)


def test_revoke_not_repair_and_wrong_token_does_not_revoke(auth):
    service, _ = auth
    token, _, identity = service.pair(service.pairing_secret)
    assert service.revoke("wrong") is None
    assert service.authenticate(token) is identity
    assert service.revoke(token) is identity
    assert service.revoke(token) is None
    with pytest.raises(LocalWebRejected, match="^session_refused$"):
        service.authenticate(token)
    with pytest.raises(LocalWebRejected, match="^pairing_unavailable$"):
        service.pair(service.pairing_secret)


def test_close_before_or_after_pair(auth):
    service, _ = auth
    service.close()
    with pytest.raises(LocalWebRejected, match="^pairing_unavailable$"):
        service.pair(service.pairing_secret)
    other = LocalAuth()
    token, _, _ = other.pair(other.pairing_secret)
    other.close()
    with pytest.raises(LocalWebRejected, match="^session_refused$"):
        other.authenticate(token)


@pytest.mark.parametrize("badclock", [True, None, "100", math.nan, math.inf, -math.inf])
def test_invalid_clock_returns_content_free_failure(badclock):
    with pytest.raises(LocalWebRejected, match="^auth_unavailable$"):
        LocalAuth(clock=lambda: badclock)


def test_throwing_clock_is_not_reflected():
    def fail():
        raise RuntimeError("private clock payload")

    with pytest.raises(LocalWebRejected, match="^auth_unavailable$") as caught:
        LocalAuth(clock=fail)
    assert "private" not in str(caught.value)


@pytest.mark.parametrize(
    "ticket", ["bad", "web-request-" + "0" * 31, "web-request-" + "A" * 32, 1, [], {}]
)
def test_session_payload_refuses_untrusted_ticket(auth, ticket):
    service, _ = auth
    token, _, _ = service.pair(service.pairing_secret)
    with pytest.raises(LocalWebRejected, match="^auth_unavailable$"):
        service.session_payload(token, ticket)


def test_session_payload_accepts_exact_ticket(auth):
    service, _ = auth
    token, _, _ = service.pair(service.pairing_secret)
    ticket = "web-request-" + "a" * 32
    assert service.session_payload(token, ticket)["last_ticket"] == ticket


def test_simultaneous_pairing_mints_only_one_session(auth):
    service, _ = auth

    def attempt():
        try:
            return service.pair(service.pairing_secret)
        except LocalWebRejected as error:
            return error.code

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: attempt(), range(8)))
    accepted = [result for result in results if type(result) is tuple]
    assert len(accepted) == 1
    assert results.count("pairing_unavailable") == 7
    token, _, identity = accepted[0]
    assert service.authenticate(token) is identity


def test_clock_failure_after_pair_denies_existing_session(auth):
    service, clock = auth
    token, _, _ = service.pair(service.pairing_secret)
    clock.value = math.nan
    with pytest.raises(LocalWebRejected, match="^auth_unavailable$"):
        service.authenticate(token)


def test_clock_rollback_before_pair_denies_and_does_not_extend_deadline(auth):
    service, clock = auth
    clock.value = 99
    with pytest.raises(LocalWebRejected, match="^auth_unavailable$"):
        service.pair(service.pairing_secret)
    clock.value = 220
    with pytest.raises(LocalWebRejected, match="^pairing_unavailable$"):
        service.pair(service.pairing_secret)


@pytest.mark.parametrize("method", ["authenticate", "csrf", "session_payload"])
def test_clock_rollback_after_pair_denies_existing_session(auth, method):
    service, clock = auth
    token, csrf, _ = service.pair(service.pairing_secret)
    clock.value = 101
    assert service.authenticate(token)
    clock.value = 100
    args = (
        (token, csrf)
        if method == "csrf"
        else ((token, None) if method == "session_payload" else (token,))
    )
    with pytest.raises(LocalWebRejected, match="^auth_unavailable$"):
        getattr(service, method)(*args)
    clock.value = 1000
    with pytest.raises(LocalWebRejected, match="^session_refused$"):
        service.authenticate(token)


def test_oversized_integer_clock_is_content_free():
    with pytest.raises(LocalWebRejected, match="^auth_unavailable$"):
        LocalAuth(clock=lambda: 10**1000)
