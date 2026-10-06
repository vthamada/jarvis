"""Offline OIDC ID-token verification against an explicitly supplied JWKS.

RS256 is the only supported signing algorithm in this slice; unfamiliar
algorithms fail closed. PyJWT/cryptography verifies the signature, never local
signature code. Numeric dates are checked after verification against the
caller's explicit clock (PyJWT otherwise uses the process wall clock). The
five-second skew is fixed, not caller-configurable. Nothing here fetches keys,
reads credentials, associates a JARVIS principal or grants action authority.
"""

from __future__ import annotations

import base64
import hmac
import json
import math
import re

from .siwc_contracts import ISSUER, SiwcError, VerifiedIdentity, valid_client_id, valid_subject

_B64 = re.compile(r"[A-Za-z0-9_-]+\Z")
_MAX_TOKEN = 16_384
_MAX_JSON = 131_072
_SKEW = 5
_FORBIDDEN_HEADER = {"jku", "jwk", "x5u", "x5c", "crit", "b64"}


def _refuse() -> None:
    raise SiwcError("siwc_id_token_invalid")


def _visible(value: object, *, limit: int = 256) -> bool:
    return (type(value) is str and 1 <= len(value) <= limit
            and all(33 <= ord(char) <= 126 for char in value))


def _tree(value: object, depth: int = 0, budget: list[int] | None = None) -> None:
    """Bound both parsed JWT claims and the trusted-composition JWKS object."""
    if budget is None:
        budget = [2048, _MAX_JSON]
    budget[0] -= 1
    if budget[0] < 0 or depth > 8:
        _refuse()
    if type(value) is dict:
        if len(value) > 128:
            _refuse()
        for key, item in value.items():
            if not _visible(key, limit=256):
                _refuse()
            budget[1] -= len(key)
            _tree(item, depth + 1, budget)
    elif type(value) is list:
        if len(value) > 128:
            _refuse()
        for item in value:
            _tree(item, depth + 1, budget)
    elif type(value) is str:
        budget[1] -= len(value)
        if len(value) > 8192 or any(
                ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
                or ord(char) in (0x2028, 0x2029)
                or 0x202A <= ord(char) <= 0x202E or 0x2066 <= ord(char) <= 0x2069
                for char in value):
            _refuse()
    elif type(value) is int:
        if value.bit_length() > 64:
            _refuse()
    elif type(value) is float:
        if not math.isfinite(value):
            _refuse()
    elif value is not None and type(value) is not bool:
        _refuse()
    if budget[1] < 0:
        _refuse()


def _pairs(items: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in items:
        if key in result:
            _refuse()
        result[key] = value
    return result


def _decode(segment: object, *, limit: int) -> bytes:
    if (type(segment) is not str or not 1 <= len(segment) <= limit
            or _B64.fullmatch(segment) is None or len(segment) % 4 == 1):
        _refuse()
    decoded = base64.b64decode(segment + "=" * (-len(segment) % 4), altchars=b"-_", validate=True)
    if base64.urlsafe_b64encode(decoded).rstrip(b"=").decode("ascii") != segment:
        _refuse()
    return decoded


def _json(segment: str, *, limit: int) -> dict:
    # Reject duplicate keys and non-standard JSON before the library parses it.
    def invalid_constant(_value):
        _refuse()

    value = json.loads(_decode(segment, limit=limit).decode("utf-8"),
                       object_pairs_hook=_pairs, parse_constant=invalid_constant)
    if type(value) is not dict:
        _refuse()
    _tree(value)
    return value


def _key(jwks: object, kid: str) -> dict:
    if type(jwks) is not dict:
        _refuse()
    _tree(jwks)
    if len(json.dumps(jwks, ensure_ascii=True, allow_nan=False)) > _MAX_JSON:
        _refuse()
    keys = jwks.get("keys")
    if type(keys) is not list or not 1 <= len(keys) <= 32 or any(type(k) is not dict for k in keys):
        _refuse()
    matches = [key for key in keys if key.get("kid") == kid]
    if len(matches) != 1:
        _refuse()
    key = matches[0]
    if (key.get("kty") != "RSA" or key.get("use", "sig") != "sig"
            or key.get("alg", "RS256") != "RS256"
            or any(name in key for name in ("d", "p", "q", "dp", "dq", "qi", "oth", "k"))):
        _refuse()
    if "key_ops" in key and key["key_ops"] != ["verify"]:
        _refuse()
    modulus = _decode(key.get("n"), limit=1366)
    exponent = _decode(key.get("e"), limit=8)
    if (not modulus or modulus[0] == 0 or not exponent or exponent[0] == 0
            or not 2048 <= int.from_bytes(modulus, "big").bit_length() <= 8192
            or int.from_bytes(modulus, "big") % 2 != 1
            or not 3 <= int.from_bytes(exponent, "big") <= 0xFFFFFFFF
            or int.from_bytes(exponent, "big") % 2 != 1):
        _refuse()
    # Only pass the vetted public material to the library, not remote metadata.
    return {"kty": "RSA", "n": key["n"], "e": key["e"]}


def _date(value: object) -> int:
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not 0 <= value <= 2**53 - 1 or int(value) != value):
        _refuse()
    return int(value)


def _verify(token: str, *, jwks: dict, client_id: str, nonce: str | None,
            expected_identity: VerifiedIdentity | None, now: float) -> VerifiedIdentity:
    if (not valid_client_id(client_id) or type(now) not in (int, float)
            or not math.isfinite(now) or not 0 <= now <= 2**53 - 1
            or (nonce is not None and not _visible(nonce))
            or (nonce is None and type(expected_identity) is not VerifiedIdentity)
            or (expected_identity is not None and type(expected_identity) is not VerifiedIdentity)):
        _refuse()
    if type(token) is not str or not 1 <= len(token) <= _MAX_TOKEN or token.count(".") != 2:
        _refuse()
    header_segment, payload_segment, signature_segment = token.split(".")
    header = _json(header_segment, limit=2048)
    payload = _json(payload_segment, limit=12_288)
    if (header.get("alg") != "RS256" or not _visible(header.get("kid"))
            or _FORBIDDEN_HEADER.intersection(header)
            or ("typ" in header and header["typ"] != "JWT")):
        _refuse()
    key = _key(jwks, header["kid"])
    signature = _decode(signature_segment, limit=1366)
    if len(signature) != len(_decode(key["n"], limit=1366)):
        _refuse()
    try:
        import jwt
    except ImportError:
        raise SiwcError("siwc_identity_dependency_missing") from None
    # All semantic checks below follow signature verification. We intentionally
    # disable only the library's wall-clock/claim checks, not its signature.
    verified = jwt.decode(token, jwt.algorithms.RSAAlgorithm.from_jwk(key), algorithms=["RS256"],
                          options={"verify_signature": True, "verify_exp": False,
                                   "verify_iat": False, "verify_nbf": False,
                                   "verify_aud": False, "verify_iss": False,
                                   "verify_sub": False, "verify_jti": False})
    if verified != payload:
        _refuse()
    if payload.get("iss") != ISSUER or not valid_subject(payload.get("sub")):
        _refuse()
    audience = payload.get("aud")
    if type(audience) is str:
        if audience != client_id:
            _refuse()
    elif type(audience) is list:
        if (not 1 <= len(audience) <= 16 or any(not _visible(aud) for aud in audience)
                or len(set(audience)) != len(audience) or client_id not in audience
                or (len(audience) > 1 and payload.get("azp") != client_id)):
            _refuse()
    else:
        _refuse()
    if "azp" in payload and payload["azp"] != client_id:
        _refuse()
    expires, issued = _date(payload.get("exp")), _date(payload.get("iat"))
    if expires <= issued or now >= expires + _SKEW or issued > now + _SKEW:
        _refuse()
    if "nbf" in payload:
        not_before = _date(payload["nbf"])
        if not_before >= expires or not_before > now + _SKEW:
            _refuse()
    if nonce is not None:
        if not _visible(payload.get("nonce")) or not hmac.compare_digest(payload["nonce"], nonce):
            _refuse()
    identity = VerifiedIdentity(client_id=client_id, subject=payload["sub"],
                                email=payload.get("email"))
    if expected_identity is not None and (
            identity.issuer != expected_identity.issuer
            or not hmac.compare_digest(identity.client_id, expected_identity.client_id)
            or not hmac.compare_digest(identity.subject, expected_identity.subject)):
        _refuse()
    return identity


def verify_id_token(token: str, *, jwks: dict, client_id: str, nonce: str | None,
                    expected_identity: VerifiedIdentity | None = None,
                    now: float) -> VerifiedIdentity:
    """Verify authorization nonce, or refresh's exact prior account binding.

    ``nonce=None`` is restricted to refresh with a previously verified identity.
    Email is optional display metadata, never the account-binding identifier.
    Missing optional JWT/crypto dependencies fail closed, with no fallback.
    Diagnostics are constants, never parsed token/key data or library errors.
    """
    try:
        return _verify(token, jwks=jwks, client_id=client_id, nonce=nonce,
                       expected_identity=expected_identity, now=now)
    except SiwcError as exc:
        code = ("siwc_identity_dependency_missing" if exc.code == "siwc_identity_dependency_missing"
                else "siwc_id_token_invalid")
        raise SiwcError(code) from None
    except Exception:
        raise SiwcError("siwc_id_token_invalid") from None
