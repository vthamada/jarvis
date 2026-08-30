"""Canonical, fail-closed semantics for reviewed technology radar intake."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from hashlib import sha256
from ipaddress import ip_address
from json import dumps
from re import IGNORECASE, fullmatch
from re import compile as compile_pattern
from typing import Any
from unicodedata import category, normalize
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from shared.contracts import TechnologyRadarIntakeContract
from shared.technology_absorption import VALID_ABSORPTION_CLASSES
from shared.versioning import parse_canonical_semver

VALID_TECHNOLOGY_SOURCE_KINDS = frozenset(
    {"repository", "skill", "standard", "article"}
)
VALID_TECHNOLOGY_LICENSE_STATUSES = frozenset(
    {"declared", "unknown_requires_review"}
)
VALID_TECHNOLOGY_INTAKE_REVIEW_STATUSES = frozenset(
    {"approved_for_radar_intake"}
)
TECHNOLOGY_SOURCE_TRUST_STATUS = "operator_attested_untrusted_reference"
TECHNOLOGY_INTAKE_STATUS = "reviewed_reference"

_SHA256_PATTERN = r"[0-9a-f]{64}"
_CANONICAL_REF_PATTERN = r"[a-z][a-z0-9+.-]*://[^\s\x00-\x1f\x7f]{1,500}"
_MAX_LIST_ITEMS = 32
_MAX_TEXT_LENGTH = 1000
_MAX_LOCATOR_LENGTH = 2048
_MAX_CLOCK_SKEW_SECONDS = 300
_AUTHORITY_FALSE_FIELDS = (
    "network_fetch_allowed",
    "knowledge_ingestion_allowed",
    "dependency_installation_allowed",
    "execution_allowed",
    "runtime_activation_allowed",
    "promotion_authorized",
    "automatic_promotion_allowed",
    "core_mutation_allowed",
    "priority_mutation_allowed",
)
_REVIEW_METADATA_FIELDS = frozenset(
    {
        "reviewed_payload_fingerprint",
        "reviewer_ref",
        "review_status",
        "review_evidence_refs",
        "reviewed_at",
        "recorded_at",
    }
)
_SENSITIVE_ASSIGNMENT = compile_pattern(
    r"\b(api[-_]?key|access[-_]?token|auth[-_]?token|client[-_]?secret|"
    r"aws[-_]?secret[-_]?access[-_]?key|private[-_]?key|token|password|passwd|secret)"
    r"\s*[:=]\s*[^\s,;]+",
    IGNORECASE,
)
_BEARER_TOKEN = compile_pattern(r"\bBearer\s+[^\s,;]+", IGNORECASE)
_AUTHORIZATION_HEADER = compile_pattern(
    r"\bAuthorization\s*:\s*(?:Basic|Api[- ]?Key)\s+[^\s,;]+",
    IGNORECASE,
)
_AUTHENTICATED_URL = compile_pattern(r"://[^\s/:@]+:[^@\s]+@", IGNORECASE)
_PRIVATE_PATH = compile_pattern(
    r"(?:\b[A-Za-z]:[\\/]|(?<![:\w])/(?:Users|home|root|tmp|var|etc|run|opt)/)",
    IGNORECASE,
)
_PRIVATE_KEY_BLOCK = compile_pattern(
    r"-----BEGIN(?: [A-Z0-9]+)? PRIVATE KEY-----",
    IGNORECASE,
)
_STANDALONE_CREDENTIAL = compile_pattern(
    r"(?:\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{16,255}\b"
    r"|\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{16,255}\b"
    r"|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
    r"|\bglpat-[A-Za-z0-9_-]{16,255}\b"
    r"|\bxox[baprs]-[A-Za-z0-9-]{16,255}\b"
    r"|\b(?:sk|rk)_live_[A-Za-z0-9]{16,255}\b"
    r"|\bAIza[0-9A-Za-z_-]{31,255}\b"
    r"|\bnpm_[A-Za-z0-9]{16,255}\b)",
)
_SENSITIVE_QUERY_KEYS = {
    "api_key",
    "apikey",
    "access_token",
    "auth_token",
    "token",
    "password",
    "passwd",
    "secret",
    "signature",
    "sig",
    "client_secret",
    "clientsecret",
    "secret_key",
    "secretkey",
    "x_amz_credential",
    "x_amz_signature",
    "x_amz_security_token",
    "x_goog_credential",
    "x_goog_signature",
    "private_token",
    "awsaccesskeyid",
    "googleaccessid",
}


def canonical_technology_radar_intake_payload(value: object) -> str:
    """Serialize an intake deterministically for immutable persistence."""

    payload: Any = asdict(value) if is_dataclass(value) else value
    return dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def technology_radar_intake_fingerprint(value: object) -> str:
    """Return the SHA-256 identity of the complete canonical intake."""

    return sha256(canonical_technology_radar_intake_payload(value).encode("utf-8")).hexdigest()


def technology_radar_review_subject_fingerprint(
    intake: TechnologyRadarIntakeContract,
) -> str:
    """Bind human review to every substantive intake and lineage field."""

    subject = {
        key: value
        for key, value in asdict(intake).items()
        if key not in _REVIEW_METADATA_FIELDS
    }
    return technology_radar_intake_fingerprint(subject)


def technology_radar_source_identity(
    source_locator: str,
    source_version_ref: str,
) -> tuple[str, str]:
    """Return the shared canonical tuple used for source deduplication."""

    canonical_locator = canonicalize_technology_source_locator(source_locator)
    canonical_version_ref = _canonicalize_technology_source_version_ref(
        source_version_ref
    )
    blockers: list[str] = []
    _validate_ref(canonical_version_ref, "source_version_ref", blockers)
    if blockers or _contains_sensitive_material(canonical_version_ref):
        raise ValueError("technology source version ref must be canonical")
    if canonical_version_ref != source_version_ref:
        raise ValueError("technology source version ref must be canonical")
    return canonical_locator, canonical_version_ref


def canonicalize_technology_source_locator(value: str) -> str:
    """Return the canonical public HTTPS locator without performing network I/O."""

    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("technology source locator must be canonical text")
    if (
        len(value) > _MAX_LOCATOR_LENGTH
        or not value.isascii()
        or _has_control_character(value)
    ):
        raise ValueError("technology source locator is not bounded text")
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise ValueError("technology source locator must use HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("technology source locator cannot contain userinfo")
    if not parsed.hostname:
        raise ValueError("technology source locator requires a host")
    host = parsed.hostname.lower().rstrip(".")
    if not host.isascii():
        raise ValueError("technology source locator requires an ASCII host")
    if _non_public_host(host):
        raise ValueError("technology source locator requires a public host")
    if not _valid_hostname_syntax(host):
        raise ValueError("technology source locator host is not canonical")
    if parsed.fragment:
        raise ValueError("technology source locator cannot contain a fragment")
    query_items = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=False)
    if any(
        _has_control_character(key) or _has_control_character(query_value)
        for key, query_value in query_items
    ):
        raise ValueError("technology source locator query contains control characters")
    if any(
        key.lower() in _SENSITIVE_QUERY_KEYS
        or key.lower().replace("-", "_") in _SENSITIVE_QUERY_KEYS
        for key, _value in query_items
    ):
        raise ValueError("technology source locator cannot contain a sensitive query")
    query = urlencode(sorted(query_items), doseq=True)
    port = parsed.port
    netloc = host if port in {None, 443} else f"{host}:{port}"
    decoded_path = unquote(parsed.path)
    if (
        "\\" in decoded_path
        or _has_control_character(decoded_path)
        or any(segment in {".", ".."} for segment in decoded_path.split("/"))
    ):
        raise ValueError("technology source locator path is not canonical")
    path = quote(decoded_path, safe="/:@-._~!$&'()*+,;=") or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(("https", netloc, path, query, ""))


def _canonicalize_technology_source_version_ref(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("technology source version ref must be canonical")
    if not value.isascii() or _has_control_character(value):
        raise ValueError("technology source version ref must be canonical")
    parsed = urlsplit(value)
    if (
        not parsed.scheme
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("technology source version ref must be canonical")
    decoded_netloc = unquote(parsed.netloc)
    if (
        not decoded_netloc.isascii()
        or _has_control_character(decoded_netloc)
        or not fullmatch(r"[A-Za-z0-9.-]{1,253}", decoded_netloc)
    ):
        raise ValueError("technology source version ref must be canonical")
    canonical_netloc = decoded_netloc.lower().rstrip(".")
    decoded_path = unquote(parsed.path)
    if (
        "\\" in decoded_path
        or _has_control_character(decoded_path)
        or any(segment in {".", ".."} for segment in decoded_path.split("/"))
    ):
        raise ValueError("technology source version ref must be canonical")
    path = quote(decoded_path, safe="/:@-._~!$&'()*+,;=")
    return urlunsplit((parsed.scheme.lower(), canonical_netloc, path, "", ""))


def validate_technology_radar_intake(
    intake: TechnologyRadarIntakeContract,
    *,
    now: datetime | None = None,
) -> list[str]:
    """Return deterministic blockers without trusting or activating the source."""

    blockers: list[str] = []
    if not isinstance(intake, TechnologyRadarIntakeContract):
        return ["technology_radar_intake_contract_required"]

    _validate_ref(intake.intake_id, "intake_id", blockers)
    _validate_ref(intake.candidate_ref, "candidate_ref", blockers)
    if parse_canonical_semver(intake.intake_version) is None:
        blockers.append("invalid_intake_version")
    _validate_text(intake.technology_name, "technology_name", blockers)
    if intake.source_kind not in VALID_TECHNOLOGY_SOURCE_KINDS:
        blockers.append("invalid_source_kind")
    _validate_locator(intake.source_locator, blockers)
    _validate_ref(intake.source_version_ref, "source_version_ref", blockers)
    _validate_sha256(
        intake.source_content_sha256,
        "source_content_sha256",
        blockers,
    )
    _validate_text(intake.license_id, "license_id", blockers, max_length=128)
    if isinstance(intake.license_id, str) and fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9.+-]{0,127}",
        intake.license_id,
    ) is None:
        blockers.append("invalid_license_id")
    if intake.license_status not in VALID_TECHNOLOGY_LICENSE_STATUSES:
        blockers.append("invalid_license_status")
    if (
        intake.license_id == "NOASSERTION"
        and intake.license_status != "unknown_requires_review"
    ) or (
        intake.license_id != "NOASSERTION"
        and intake.license_status == "unknown_requires_review"
    ):
        blockers.append("license_status_mismatch")
    _validate_ref(intake.license_evidence_ref, "license_evidence_ref", blockers)
    retrieved_at = _validate_timestamp(intake.retrieved_at, "retrieved_at", blockers)
    _validate_string_list(intake.claims, "claims", blockers)
    _validate_string_list(intake.risks, "risks", blockers)
    if intake.absorption_class not in VALID_ABSORPTION_CLASSES:
        blockers.append("unknown_absorption_class")
    _validate_string_list(intake.target_gap_refs, "target_gap_refs", blockers)
    if isinstance(intake.target_gap_refs, list):
        for target_gap_ref in intake.target_gap_refs:
            if not isinstance(target_gap_ref, str) or fullmatch(
                r"[A-Z][A-Z0-9]{1,15}-[0-9]{3,6}",
                target_gap_ref,
            ) is None:
                blockers.append("invalid_target_gap_ref")
    _validate_ref(intake.research_approval_ref, "research_approval_ref", blockers)
    _validate_sha256(
        intake.reviewed_payload_fingerprint,
        "reviewed_payload_fingerprint",
        blockers,
    )
    if intake.reviewed_payload_fingerprint != technology_radar_review_subject_fingerprint(
        intake
    ):
        blockers.append("reviewed_payload_fingerprint_mismatch")
    _validate_ref(intake.reviewer_ref, "reviewer_ref", blockers)
    if intake.review_status not in VALID_TECHNOLOGY_INTAKE_REVIEW_STATUSES:
        blockers.append("invalid_review_status")
    _validate_string_list(
        intake.review_evidence_refs,
        "review_evidence_refs",
        blockers,
    )
    if isinstance(intake.review_evidence_refs, list):
        for review_evidence_ref in intake.review_evidence_refs:
            _validate_ref(
                review_evidence_ref,
                "review_evidence_ref",
                blockers,
            )
    reviewed_at = _validate_timestamp(intake.reviewed_at, "reviewed_at", blockers)
    recorded_at = _validate_timestamp(intake.recorded_at, "recorded_at", blockers)

    if retrieved_at and reviewed_at and reviewed_at < retrieved_at:
        blockers.append("review_before_source_retrieval")
    if reviewed_at and recorded_at and recorded_at < reviewed_at:
        blockers.append("record_before_human_review")
    comparison_now = _utc_datetime(now or datetime.now(UTC))
    if recorded_at and recorded_at.timestamp() > (
        comparison_now.timestamp() + _MAX_CLOCK_SKEW_SECONDS
    ):
        blockers.append("recorded_at_in_future")
    if reviewed_at and reviewed_at.timestamp() > (
        comparison_now.timestamp() + _MAX_CLOCK_SKEW_SECONDS
    ):
        blockers.append("reviewed_at_in_future")
    if retrieved_at and retrieved_at.timestamp() > (
        comparison_now.timestamp() + _MAX_CLOCK_SKEW_SECONDS
    ):
        blockers.append("retrieved_at_in_future")

    previous_id = intake.previous_intake_id
    previous_fingerprint = intake.previous_intake_fingerprint
    parsed_intake_version = parse_canonical_semver(intake.intake_version)
    if bool(previous_id) != bool(previous_fingerprint):
        blockers.append("previous_intake_lineage_pair_required")
    if parsed_intake_version == (1, 0, 0) and (previous_id or previous_fingerprint):
        blockers.append("genesis_intake_cannot_claim_predecessor")
    if parsed_intake_version is not None and parsed_intake_version != (1, 0, 0) and not (
        previous_id and previous_fingerprint
    ):
        blockers.append("versioned_intake_requires_predecessor")
    if isinstance(intake.intake_id, str) and isinstance(intake.intake_version, str) and not (
        intake.intake_id.endswith(f"/{intake.intake_version}")
    ):
        blockers.append("intake_id_version_mismatch")
    if previous_id:
        _validate_ref(previous_id, "previous_intake_id", blockers)
        if previous_id == intake.intake_id:
            blockers.append("previous_intake_cannot_reference_self")
    if previous_fingerprint:
        _validate_sha256(
            previous_fingerprint,
            "previous_intake_fingerprint",
            blockers,
        )

    if intake.source_trust_status != TECHNOLOGY_SOURCE_TRUST_STATUS:
        blockers.append("source_trust_status_not_allowed")
    if intake.intake_status != TECHNOLOGY_INTAKE_STATUS:
        blockers.append("intake_status_not_allowed")
    if intake.read_only is not True:
        blockers.append("read_only_must_be_true")
    if intake.immutable is not True:
        blockers.append("immutable_must_be_true")
    if intake.human_review_required is not True:
        blockers.append("human_review_required_must_be_true")
    for field_name in _AUTHORITY_FALSE_FIELDS:
        if getattr(intake, field_name) is not False:
            blockers.append(f"{field_name}_must_be_false")

    _validate_sensitive_material(intake, blockers)
    return sorted(set(blockers))


def require_valid_technology_radar_intake(
    intake: TechnologyRadarIntakeContract,
    *,
    now: datetime | None = None,
) -> TechnologyRadarIntakeContract:
    """Return the intake or raise before any persistence side effect."""

    blockers = validate_technology_radar_intake(intake, now=now)
    if blockers:
        raise ValueError(f"invalid technology radar intake: {','.join(blockers)}")
    return intake


def _validate_locator(value: object, blockers: list[str]) -> None:
    if not isinstance(value, str):
        blockers.append("invalid_source_locator")
        return
    try:
        canonical = canonicalize_technology_source_locator(value)
    except ValueError as exc:
        message = str(exc)
        if "HTTPS" in message:
            blockers.append("source_locator_https_required")
        elif "userinfo" in message:
            blockers.append("source_locator_userinfo_forbidden")
        elif "public host" in message:
            blockers.append("source_locator_non_public_host")
        elif "sensitive query" in message:
            blockers.append("source_locator_sensitive_query_forbidden")
        elif "fragment" in message:
            blockers.append("source_locator_fragment_forbidden")
        else:
            blockers.append("invalid_source_locator")
        return
    if canonical != value:
        blockers.append("source_locator_not_canonical")


def _validate_ref(value: object, field_name: str, blockers: list[str]) -> None:
    if (
        not isinstance(value, str)
        or not value.isascii()
        or fullmatch(_CANONICAL_REF_PATTERN, value) is None
    ):
        blockers.append(f"invalid_{field_name}")
        return
    decoded = unquote(value)
    if _has_control_character(decoded):
        blockers.append(f"invalid_{field_name}")


def _validate_sha256(value: object, field_name: str, blockers: list[str]) -> None:
    if not isinstance(value, str) or fullmatch(_SHA256_PATTERN, value) is None:
        blockers.append(f"invalid_{field_name}")


def _validate_text(
    value: object,
    field_name: str,
    blockers: list[str],
    *,
    max_length: int = _MAX_TEXT_LENGTH,
) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        blockers.append(f"invalid_{field_name}")
        return
    if len(value) > max_length:
        blockers.append(f"{field_name}_too_long")
    if _has_control_character(value):
        blockers.append(f"{field_name}_contains_control_character")


def _validate_string_list(
    values: object,
    field_name: str,
    blockers: list[str],
) -> None:
    if not isinstance(values, list) or not values:
        blockers.append(f"{field_name}_required")
        return
    if len(values) > _MAX_LIST_ITEMS:
        blockers.append(f"{field_name}_too_many_items")
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value or value != value.strip():
            blockers.append(f"{field_name}_contains_invalid_item")
            continue
        if len(value) > _MAX_TEXT_LENGTH:
            blockers.append(f"{field_name}_item_too_long")
        if _has_control_character(value):
            blockers.append(f"{field_name}_contains_control_character")
        canonical_identity = normalize("NFKC", value).casefold()
        if canonical_identity in seen:
            blockers.append(f"{field_name}_duplicate:{canonical_identity}")
        seen.add(canonical_identity)


def _validate_timestamp(
    value: object,
    field_name: str,
    blockers: list[str],
) -> datetime | None:
    if not isinstance(value, str) or not value or value != value.strip():
        blockers.append(f"invalid_{field_name}")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        blockers.append(f"invalid_{field_name}")
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        blockers.append(f"invalid_{field_name}")
        return None
    if parsed.utcoffset().total_seconds() != 0:
        blockers.append(f"invalid_{field_name}")
        return None
    return _utc_datetime(parsed)


def _validate_sensitive_material(
    intake: TechnologyRadarIntakeContract,
    blockers: list[str],
) -> None:
    fields: dict[str, Iterable[str]] = {
        "intake_id": [intake.intake_id],
        "candidate_ref": [intake.candidate_ref],
        "technology_name": [intake.technology_name],
        "source_locator": [intake.source_locator],
        "source_version_ref": [intake.source_version_ref],
        "license_evidence_ref": [intake.license_evidence_ref],
        "claims": intake.claims,
        "risks": intake.risks,
        "target_gap_refs": intake.target_gap_refs,
        "research_approval_ref": [intake.research_approval_ref],
        "reviewer_ref": [intake.reviewer_ref],
        "review_evidence_refs": intake.review_evidence_refs,
    }
    for field_name, values in fields.items():
        if any(_contains_sensitive_material(value) for value in values):
            blockers.append(f"sensitive_material_detected:{field_name}")


def _contains_sensitive_material(value: object) -> bool:
    if not isinstance(value, str):
        return False
    decoded = unquote(value)
    return any(
        pattern.search(decoded) is not None
        for pattern in (
            _SENSITIVE_ASSIGNMENT,
            _BEARER_TOKEN,
            _AUTHORIZATION_HEADER,
            _AUTHENTICATED_URL,
            _PRIVATE_PATH,
            _PRIVATE_KEY_BLOCK,
            _STANDALONE_CREDENTIAL,
        )
    )


def technology_text_contains_sensitive_material(value: object) -> bool:
    """Expose the canonical high-confidence secret/path screen to inert tools."""

    return _contains_sensitive_material(value)


def _has_control_character(value: str) -> bool:
    return any(category(character) in {"Cc", "Cf"} for character in value)


def _non_public_host(host: str) -> bool:
    if (
        host == "localhost"
        or host.endswith(
            (
                ".localhost",
                ".local",
                ".internal",
                ".invalid",
                ".test",
                ".onion",
                ".lan",
                ".home",
                ".corp",
            )
        )
        or "." not in host
    ):
        return True
    try:
        ip_address(host)
    except ValueError:
        return False
    return True


def _valid_hostname_syntax(host: str) -> bool:
    labels = host.split(".")
    if len(host) > 253 or len(labels[-1]) < 2:
        return False
    return all(
        1 <= len(label) <= 63
        and label[0].isalnum()
        and label[-1].isalnum()
        and all(character.isalnum() or character == "-" for character in label)
        for label in labels
    )


def _utc_datetime(value: datetime) -> datetime:
    return value.astimezone(UTC)
