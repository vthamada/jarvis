"""Local provider-account records; never JARVIS principals or action grants.

These records cross trusted Python composition, not a public JSON authority
boundary. Signature validation belongs to the identity verifier before account
activation. Tokens and identity bindings are deliberately absent from repr.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass, field

ISSUER = "https://auth.openai.com"
RESOURCE = "https://api.openai.com/v1"
DIRECT_SCOPE = "chatgpt.tokens.use.direct"
REQUESTED_SCOPES = ("openid", "profile", "email", "offline_access", "resource.invoke", DIRECT_SCOPE)
_CLIENT = re.compile(r"oaiapp_[A-Za-z0-9_-]{1,160}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9._~+/\-]+=*\Z")


class SiwcError(ValueError):
    """Fixed diagnostics only; never include callback, claims or credentials."""

    def __init__(self, code: str = "siwc_refused"):
        # Codes are infrastructure constants, not external response text.
        if type(code) is not str or re.fullmatch(r"siwc_[a-z_]{1,64}", code) is None:
            code = "siwc_refused"
        self.code = code
        super().__init__(code)


def valid_client_id(value: object) -> bool:
    return type(value) is str and _CLIENT.fullmatch(value) is not None


def valid_host_id(value: object) -> bool:
    # This implementation chooses the supported UUIDv4 host-ID variant.
    if type(value) is not str or not value.startswith("urn:uuid:"):
        return False
    try:
        parsed = uuid.UUID(value[9:])
        return parsed.version == 4 and value == "urn:uuid:" + str(parsed)
    except ValueError:
        return False


def finite_number(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def valid_token(value: object) -> bool:
    return type(value) is str and 1 <= len(value) <= 16_384 and _TOKEN.fullmatch(value) is not None


def valid_subject(value: object) -> bool:
    return (type(value) is str and 1 <= len(value) <= 256
            and all(33 <= ord(char) <= 126 for char in value))


@dataclass(frozen=True)
class VerifiedIdentity:
    client_id: str = field(repr=False)
    subject: str = field(repr=False)
    email: str | None = field(default=None, repr=False)
    issuer: str = ISSUER

    def __post_init__(self):
        if (self.issuer != ISSUER or not valid_client_id(self.client_id)
                or not valid_subject(self.subject)
                or (self.email is not None and (type(self.email) is not str
                    or not 1 <= len(self.email) <= 320
                    or any(ord(c) < 32 or ord(c) > 126 for c in self.email)))):
            raise SiwcError("siwc_identity_invalid")


@dataclass(frozen=True)
class SiwcCredentials:
    client_id: str = field(repr=False)
    host_id: str = field(repr=False)
    subject: str = field(repr=False)
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    id_token: str = field(repr=False)
    scopes: tuple[str, ...] = field(repr=False)
    expires_at: float
    saved_at: float
    email: str | None = field(default=None, repr=False)
    issuer: str = ISSUER

    def __post_init__(self):
        VerifiedIdentity(self.client_id, self.subject, self.email, self.issuer)
        if (not valid_host_id(self.host_id)
                or not all(valid_token(token) for token in
                           (self.access_token, self.refresh_token, self.id_token))
                or type(self.scopes) is not tuple or not 1 <= len(self.scopes) <= 32
                or any(type(scope) is not str or not 1 <= len(scope) <= 128
                       or not all(33 <= ord(c) <= 126 for c in scope) for scope in self.scopes)
                or len(set(self.scopes)) != len(self.scopes)
                or not finite_number(self.expires_at) or not finite_number(self.saved_at)
                or not 0 < self.expires_at - self.saved_at <= 604_800):
            raise SiwcError("siwc_credentials_invalid")

    @property
    def identity(self) -> VerifiedIdentity:
        return VerifiedIdentity(self.client_id, self.subject, self.email, self.issuer)

    def metadata(self) -> dict[str, object]:
        return {"mode": "siwc_provider_credentials", "authority": "none",
                "plan_scope_granted": DIRECT_SCOPE in self.scopes,
                "expires_at": self.expires_at, "saved_at": self.saved_at}
