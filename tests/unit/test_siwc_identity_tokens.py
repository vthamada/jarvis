"""Actual synthetic RSA signatures, no account credentials or external I/O."""

from __future__ import annotations

import base64
import builtins
import copy
import json

import pytest
from inference_service.identity_tokens import verify_id_token
from inference_service.siwc_contracts import ISSUER, SiwcError, VerifiedIdentity

CLIENT = "oaiapp_test_identity"
NONCE = "nonce-for-one-authorization"
NOW = 1_800_000_000


@pytest.fixture(scope="module")
def signing():
    jwt = pytest.importorskip("jwt")
    rsa = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.rsa")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    key.update(kid="key-one", alg="RS256", use="sig", key_ops=["verify"])
    return jwt, private, {"keys": [key]}


def claims(**updates):
    return {"iss": ISSUER, "aud": CLIENT, "sub": "test-subject",
            "iat": NOW - 30, "exp": NOW + 300, "nonce": NONCE,
            "email": "display@example.invalid", **updates}


def sign(signing, payload=None, header=None):
    jwt, private, _ = signing
    return jwt.encode(claims() if payload is None else payload, private,
                      algorithm="RS256", headers={"kid": "key-one", **(header or {})})


def verify(signing, token=None, **kwargs):
    return verify_id_token(sign(signing) if token is None else token,
                           jwks=kwargs.pop("jwks", signing[2]),
                           client_id=kwargs.pop("client_id", CLIENT),
                           nonce=kwargs.pop("nonce", NONCE), now=kwargs.pop("now", NOW), **kwargs)


def refused(signing, token=None, **kwargs):
    with pytest.raises(SiwcError, match=r"^siwc_id_token_invalid$") as caught:
        verify(signing, token, **kwargs)
    assert "display@example.invalid" not in repr(caught.value)
    assert "test-subject" not in str(caught.value)


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def raw_sign(signing, *, header=None, payload=None):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    body = b64(header or b'{"alg":"RS256","kid":"key-one"}') + "." + b64(
        payload or json.dumps(claims()).encode())
    return body + "." + b64(signing[1].sign(body.encode(), padding.PKCS1v15(), hashes.SHA256()))


def test_real_rsa_signature_returns_sanitized_identity(signing):
    identity = verify(signing)
    assert identity == VerifiedIdentity(CLIENT, "test-subject", "display@example.invalid")
    assert "test-subject" not in repr(identity)
    assert CLIENT not in repr(identity)
    assert "display@example.invalid" not in repr(identity)


@pytest.mark.parametrize("updates", [
    {"iss": "https://auth.openai.com/"}, {"iss": "https://example.invalid"},
    {"aud": "dynamic_agent_client"}, {"aud": "oaiapp_other"}, {"aud": None},
    {"aud": []}, {"aud": [CLIENT, CLIENT]}, {"aud": [CLIENT, 1]},
    {"aud": [CLIENT, "other"]}, {"aud": [CLIENT, "other"], "azp": "oaiapp_other"},
    {"azp": "oaiapp_other"}, {"sub": ""}, {"sub": "subject\nsecret"}, {"sub": 1},
    {"nonce": "wrong"}, {"nonce": None}, {"nonce": True},
    {"exp": NOW - 5}, {"exp": NOW - 100}, {"exp": True}, {"exp": "123"},
    {"exp": NOW + 0.5}, {"exp": float("inf")}, {"exp": -1},
    {"iat": NOW + 6}, {"iat": True}, {"iat": NOW + 0.5},
    {"iat": NOW + 300}, {"nbf": NOW + 6}, {"nbf": NOW + 300},
    {"nbf": False}, {"nbf": NOW + 0.5}, {"email": "secret\n@example.invalid"},
    {"email": "x" * 321}, {"email": False},
], ids=lambda x: str(next(iter(x))) + "-" + str(len(str(x))))
def test_invalid_signed_claims(signing, updates):
    refused(signing, sign(signing, claims(**updates)))


@pytest.mark.parametrize("missing", ["iss", "sub", "aud", "exp", "iat", "nonce"])
def test_required_claims(signing, missing):
    payload = claims()
    del payload[missing]
    refused(signing, sign(signing, payload))


@pytest.mark.parametrize("audience", [CLIENT, [CLIENT], ["other", CLIENT]])
def test_exact_audience_and_authorized_party(signing, audience):
    identity = verify(signing, sign(signing, claims(aud=audience, azp=CLIENT)))
    assert identity.subject == "test-subject"


def test_fixed_skew_uses_explicit_clock_not_wall_clock(signing):
    assert verify(signing, sign(signing, claims(exp=NOW - 4))).subject == "test-subject"
    identity = verify(signing, sign(signing, claims(iat=NOW + 5, nbf=NOW + 5)))
    assert identity.subject == "test-subject"
    refused(signing, now=NOW + 306)


def test_refresh_requires_account_binding_and_not_email(signing):
    previous = verify(signing)
    assert verify(signing, sign(signing, claims(email="changed@example.invalid")),
                  nonce=None, expected_identity=previous).subject == previous.subject
    payload = claims()
    del payload["nonce"]
    assert verify(signing, sign(signing, payload), nonce=None, expected_identity=previous)
    refused(signing, nonce=None)
    other = VerifiedIdentity(CLIENT, "other", previous.email)
    refused(signing, nonce=None, expected_identity=other)
    refused(signing, expected_identity=VerifiedIdentity("oaiapp_other", previous.subject))
    refused(signing, expected_identity={"sub": "test-subject"})


@pytest.mark.parametrize("now", [True, None, float("nan"), float("inf"), -1, 2**1000],
                         ids=["bool", "none", "nan", "inf", "negative", "huge"])
def test_invalid_clock(signing, now):
    refused(signing, now=now)


@pytest.mark.parametrize("header", [
    {"kid": "missing"}, {"kid": ""}, {"kid": None}, {"kid": "line\nbreak"},
    {"jku": "https://example.invalid/keys"}, {"jwk": {}}, {"x5u": "https://example.invalid"},
    {"x5c": []}, {"crit": []}, {"b64": True}, {"typ": "at+jwt"},
], ids=["unknownkid", "emptykid", "nullkid", "controlkid", "jku", "jwk", "x5u", "x5c",
        "crit", "b64", "access-token-type"])
def test_forbidden_headers(signing, header):
    encoded = json.dumps({"alg": "RS256", "kid": "key-one", **header}).encode()
    refused(signing, raw_sign(signing, header=encoded))


@pytest.mark.parametrize("algorithm", ["none", "HS256", "RS512", "ES256"])
def test_algorithm_confusion_refused_before_signature(signing, algorithm):
    header = json.dumps({"alg": algorithm, "kid": "key-one"}).encode()
    refused(signing, raw_sign(signing, header=header))


def test_invalid_signature_and_tampering(signing):
    token = sign(signing)
    head, body, signature = token.split(".")
    changed = b64(json.dumps(claims(sub="different-subject")).encode())
    refused(signing, ".".join([head, changed, signature]))
    refused(signing, ".".join([head, body, b64(b"x" * 256)]))
    refused(signing, ".".join([head, body, b64(b"x" * 255)]))


@pytest.mark.parametrize("updates", [
    {"kty": "oct"}, {"use": "enc"}, {"alg": "RS512"}, {"key_ops": ["sign"]},
    {"key_ops": ["verify", "sign"]}, {"key_ops": "verify"}, {"d": "private"},
    {"e": b64(b"\x02")}, {"e": b64(b"\x01")}, {"e": b64(b"\x00\x01\x00\x01")},
    {"e": b64(b"\xff" * 5)}, {"n": b64(b"\x01" * 128)},
    {"n": b64(b"\xff" * 1025)}, {"n": "bad="}, {"n": None},
], ids=["oct", "encrypt", "wrongalg", "sign", "mixedops", "stringops", "private",
        "evenexpo", "oneexpo", "leadingzero", "hugeexpo", "smallmod", "hugemod", "padding", "null"])
def test_invalid_key_material(signing, updates):
    jwks = copy.deepcopy(signing[2])
    jwks["keys"][0].update(updates)
    refused(signing, jwks=jwks)


def test_exact_one_matching_key_and_bounded_jwks(signing):
    key = signing[2]["keys"][0]
    for jwks in ({"keys": []}, {"keys": [key, key]}, {"keys": [key] * 33},
                 {"keys": [1]}, {"keys": "not-keys"}, {}, [], None):
        refused(signing, jwks=jwks)
    other = {"kid": "other", "kty": "EC", "use": "sig"}
    assert verify(signing, jwks={"keys": [other, key]})


@pytest.mark.parametrize("raw", [
    b'{"alg":"RS256","alg":"RS256","kid":"key-one"}',
    b'{"alg":"RS256","kid":"key-one","ki\\u0064":"key-one"}',
    b'{"alg":"RS256","kid":"key-one","x":"\\ud800"}',
    b'{"alg":"RS256","kid":"key-one","x":NaN}',
    b'{"alg":"RS256","kid":"key-one","x":1e999}',
    b'[]', b'"string"', b'{"alg":"RS256","kid":"key-one","x":"\\u0000"}',
], ids=["duplicate", "escapedduplicate", "surrogate", "nan", "overflow", "array",
        "string", "control"])
def test_strict_json_header(signing, raw):
    refused(signing, raw_sign(signing, header=raw))


def test_duplicate_payload_and_deep_trees(signing):
    payload = json.dumps(claims()).encode()[:-1] + b',"sub":"test-subject"}'
    refused(signing, raw_sign(signing, payload=payload))
    refused(signing, sign(signing, claims(x=[[[[[[[[[["too-deep"]]]]]]]]]])))
    refused(signing, sign(signing, claims(x="\u202eevil")))
    refused(signing, sign(signing, claims(x=2**100)))


@pytest.mark.parametrize("character", ["\u0085", "\u009b", "\u2028", "\u2029",
                                        "\u202a", "\u2069"],
                         ids=["c1newline", "c1escape", "line", "paragraph", "bidi", "bidiisolate"])
def test_control_and_bidi_claims_are_rejected(signing, character):
    refused(signing, sign(signing, claims(ignored_profile="name" + character + "value")))


@pytest.mark.parametrize("token", ["", ".", "a.b.c", "a.b.c.d", "x" * 16_385, None, True],
                         ids=["empty", "dot", "invalidb64", "fourparts", "oversize",
                              "null", "bool"])
def test_bounded_token_syntax(signing, token):
    # verify helper uses None as omitted; call verifier directly here.
    with pytest.raises(SiwcError):
        verify_id_token(token, jwks=signing[2], client_id=CLIENT, nonce=NONCE, now=NOW)


def test_padding_noncanonical_base64_and_invalid_utf8(signing):
    token = sign(signing)
    head, body, signature = token.split(".")
    refused(signing, head + "=." + body + "." + signature)
    refused(signing, head + "." + body + "." + signature[:-1] + "/")
    refused(signing, raw_sign(signing, header=b"\xff"))
    # n with unused nonzero low bits decodes to the same byte but isn't canonical.
    refused(signing, jwks={"keys": [{**signing[2]["keys"][0], "e": "Ax"}]})


def test_missing_dependency_fails_closed(signing, monkeypatch):
    original = builtins.__import__

    def without_jwt(name, *args, **kwargs):
        if name == "jwt":
            raise ImportError("private dependency diagnostic")
        return original(name, *args, **kwargs)

    token = sign(signing)
    monkeypatch.setattr(builtins, "__import__", without_jwt)
    with pytest.raises(SiwcError, match=r"^siwc_identity_dependency_missing$"):
        verify(signing, token)


def test_signature_library_runs_before_semantic_identity_checks(signing, monkeypatch):
    calls = []
    original = signing[0].decode

    def decode(*args, **kwargs):
        calls.append(kwargs["options"]["verify_signature"])
        return original(*args, **kwargs)

    monkeypatch.setattr(signing[0], "decode", decode)
    refused(signing, sign(signing, claims(iss="https://example.invalid")))
    assert calls == [True]


def test_library_exception_is_private(signing, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("token=highly-private-secret")

    monkeypatch.setattr(signing[0], "decode", broken)
    refused(signing)


@pytest.mark.parametrize("client_id", ["dynamic_agent_client", "oaiapp_", None, True,
                                      "oaiapp_x\nsecret", "oaiapp_" + "x" * 161],
                         ids=["dynamic", "empty", "null", "bool", "control", "oversize"])
def test_issued_client_required(signing, client_id):
    refused(signing, client_id=client_id)


@pytest.mark.parametrize("nonce", ["", True, "nonce\nsecret", "n" * 257],
                         ids=["empty", "bool", "control", "oversize"])
def test_authorization_nonce_input_required(signing, nonce):
    refused(signing, nonce=nonce)


def test_verifier_never_fetches_or_reads_credentials(signing, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("unexpected external I/O")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setenv("OPENAI_API_KEY", "must-never-read-credential")
    assert verify(signing).subject == "test-subject"


def test_bounded_total_jwks_tree(signing):
    jwks = copy.deepcopy(signing[2])
    jwks["nested"] = [["text"] * 128 for _ in range(128)]
    refused(signing, jwks=jwks)


def test_crypto_backend_unavailable_fails_closed(signing, monkeypatch):
    def missing(*args, **kwargs):
        raise ImportError("private crypto backend details")

    monkeypatch.setattr(signing[0].algorithms.RSAAlgorithm, "from_jwk", missing)
    refused(signing)
