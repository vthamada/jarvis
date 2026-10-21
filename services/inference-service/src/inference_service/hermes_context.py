"""Re-present one native host context using the bounded Hermes-derived replay.

This changes wire presentation only. It cannot select history from a database,
authorize a read, alter observations or repair a model proposal.
"""

from __future__ import annotations

import json

from apps.jarvis_hermes.replay import build_replay_messages


def _invalid(*_args):
    raise ValueError("invalid_hermes_host_context")


def _pairs(values):
    result = {}
    for key, value in values:
        if key in result:
            _invalid()
        result[key] = value
    return result


def replay_host_context(content: str) -> list[dict[str, str]]:
    """Keep query/history/progress semantically identical, without hidden state."""
    try:
        if type(content) is not str or not 1 <= len(content) <= 30000:
            _invalid()
        value = json.loads(content, object_pairs_hook=_pairs, parse_constant=_invalid)
        # Reject overflowed floats, surrogates and malformed unused fields too.
        json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8", "strict")
        fields = {"query", "available_resource_ids", "tool", "continuation", "observations"}
        if type(value) is not dict or set(value) not in (fields, fields | {"history"}):
            _invalid()
        history = value.pop("history", [])
        if type(history) is not list or len(history) > 3:
            _invalid()
        messages = []
        for turn in history:
            if type(turn) is not dict or set(turn) != {"query", "response"}:
                _invalid()
            messages.extend((
                {"role": "user", "content": turn["query"]},
                {"role": "assistant", "content": turn["response"]},
            ))
        query = value.pop("query")
        progress = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        return build_replay_messages(messages, query, progress)
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError):
        raise ValueError("invalid_hermes_host_context") from None
