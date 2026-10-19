"""Bounded read-side projection of canonical turns, not a second memory store.

Only same-subject, same-session rows are considered. Generated/source attachments
stay in their canonical final but never return as literal model history. Pattern
screening is a fail-closed known-sensitive-content guard, not general PII detection.
"""

from __future__ import annotations

from memory_service.repository import StoredTurn
from synthesis_engine.generative_analysis import _SENSITIVE_INPUT

from shared.model_tool_loop import ToolHistoryTurn
from shared.reviewed_knowledge import response_for_planning


def _text(value: object, maximum: int) -> bool:
    if type(value) is not str or not value.strip() or len(value) > maximum or "\x00" in value:
        return False
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeError:
        return False
    return True


def select_canonical_history(
    rows: list[StoredTurn] | tuple[StoredTurn, ...], *, subject_id: str, session_id: str,
) -> tuple[ToolHistoryTurn, ...]:
    """Newest three complete pairs, chronological, with at most 4000 characters.

    The repository must return at most six chronological rows. Ownership is
    checked independently before reading any candidate's text. Oversized,
    malformed or known-sensitive pairs are excluded whole, never clipped into
    apparently complete history. No plan fields or derived summaries are used.
    """
    if not _text(subject_id, 512) or not _text(session_id, 256):
        raise ValueError("invalid_history_scope")
    if type(rows) not in {list, tuple} or len(rows) > 6:
        raise ValueError("invalid_history_source")
    selected: list[ToolHistoryTurn] = []
    characters = 0
    for row in reversed(rows):
        if type(row) is not StoredTurn:
            raise ValueError("invalid_history_source")
        if row.user_id != subject_id or row.session_id != session_id:
            continue
        if not _text(row.request_content, 4000) or not _text(row.response_text, 65536):
            continue
        if (_SENSITIVE_INPUT.search(row.request_content)
                or _SENSITIVE_INPUT.search(row.response_text)):
            continue
        native = response_for_planning(row.response_text)
        pair_characters = len(row.request_content) + len(native)
        if not _text(native, 4000) or characters + pair_characters > 4000:
            continue
        selected.append(ToolHistoryTurn(query=row.request_content, response=native))
        characters += pair_characters
        if len(selected) == 3:
            break
    return tuple(reversed(selected))
