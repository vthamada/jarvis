"""Application-local MB231 contracts. No action or model authority is conveyed."""

import re
from dataclasses import dataclass

SESSION_SCHEMA = "jarvis-local-session-v1"
ANALYSIS_SCHEMA = "jarvis-local-analysis-v1"
ANALYSIS_GENERATIVE_SCHEMA = "jarvis-local-analysis-v2"
# Fixed Core MB229 diagnostics, not provider exceptions or user-supplied prose.
GENERATIVE_ERROR_CODES = frozenset({
    "invalid_context", "invalid_composition", "input_sensitive", "cancelled",
    "invalid_clock", "timed_out", "invalid_result", "binding_mismatch",
    "inference_failed", "output_limit", "invalid_candidate", "invalid_citation",
    "candidate_limit", "output_sensitive", "render_limit", "context_changed",
    "result_changed", "inference_unavailable", "scope_denied", "reviewed_source_invalid",
})
CLIENT_HEADER = "local-web-v1"
MAX_BODY_BYTES = 32768
MAX_QUERY_CHARACTERS = 4000
MAX_RESPONSE_CHARACTERS = 131072
SESSION_SECONDS = 900
PAIRING_SECONDS = 120
TICKET_SECONDS = 120
MAX_TICKETS = 64
TICKET_PATTERN = re.compile(r"web-request-[0-9a-f]{32}\Z", re.ASCII)


@dataclass(frozen=True)
class SessionIdentity:
    """Server-minted Core binding, not identity of an OS/human or a tool grant."""

    session_ref: str
    principal_ref: str
    canonical_user_ref: str


class LocalWebRejected(ValueError):
    """Only fixed, app-defined diagnostics may cross the HTTP boundary."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code
