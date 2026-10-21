"""Three fixed phase-bound report generation hints, never Core authority.

This is not an arbitrary-schema interface or a replacement for the loop parser.
Host progress selects a variant; selected resources, fresh IDs and exact
citations remain Core checks. Endpoints may ignore even a phase-bound hint.
"""

from __future__ import annotations

import json

TOOL_LOOP_SCHEMA_NAME = "jarvis_tool_loop_v1"
_PHASE_KINDS = (("tool_call",), ("tool_call", "final"), ("final",))


def tool_loop_response_format(allowed_kinds=("tool_call", "final")) -> dict[str, object]:
    """Return a fresh, host-owned schema with no query, source or model fields."""
    if (type(allowed_kinds) is not tuple or any(type(kind) is not str for kind in allowed_kinds)
            or allowed_kinds not in _PHASE_KINDS):
        raise ValueError("invalid_chat_response_format")

    def identifier():
        return {"type": "string", "minLength": 1, "maxLength": 80,
                "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}$"}

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": TOOL_LOOP_SCHEMA_NAME, "strict": True,
            "schema": {
                "type": "object",
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "kind": {"enum": ["tool_call"]},
                            "call_id": identifier(),
                            "tool": {"enum": ["read_local_report"]},
                            "arguments": {
                                "type": "object",
                                "properties": {"resource_id": identifier()},
                                "required": ["resource_id"], "additionalProperties": False,
                            },
                        },
                        "required": ["kind", "call_id", "tool", "arguments"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "kind": {"enum": ["final"]},
                            "analysis": {"type": "string", "minLength": 1, "maxLength": 4000},
                            "citations": {
                                "type": "array", "minItems": 1, "maxItems": 3,
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "call_id": identifier(),
                                        "quote": {"type": "string", "minLength": 1,
                                                  "maxLength": 512},
                                    },
                                    "required": ["call_id", "quote"],
                                    "additionalProperties": False,
                                },
                            },
                        },
                        "required": ["kind", "analysis", "citations"],
                        "additionalProperties": False,
                    },
                ],
            },
        },
    }
    schema = response_format["json_schema"]["schema"]
    schema["anyOf"] = [branch for branch in schema["anyOf"]
                       if branch["properties"]["kind"]["enum"][0] in allowed_kinds]
    return response_format


def _unique_object(pairs):
    result = {}
    for key, item in pairs:
        if key in result:
            raise ValueError("invalid_tool_loop_context")
        result[key] = item
    return result


def _invalid_constant(_value):
    raise ValueError("invalid_tool_loop_context")


def tool_loop_request_kinds(content: str) -> tuple[str, ...]:
    """Select a bounded host hint, never query/report instructions.

    JSON alone does not authenticate a host. The Core's existing composition
    supplies this message, and the chosen schema remains a generation hint.
    Unknown context fails before I/O; there is no fallback to a wider schema.
    """
    try:
        if type(content) is not str or not 1 <= len(content) <= 30_000:
            raise ValueError
        context = json.loads(content, object_pairs_hook=_unique_object,
                             parse_constant=_invalid_constant)
        # Also reject overflowing JSON floats and escaped invalid Unicode in
        # otherwise unused data. The complete parsed tree is bounded by input.
        json.dumps(context, ensure_ascii=False, allow_nan=False).encode("utf-8", "strict")
        if type(context) is not dict or type(context.get("continuation")) is not dict:
            raise ValueError
        kinds = context["continuation"].get("allowed_response_kinds")
        if type(kinds) is not list or any(type(kind) is not str for kind in kinds):
            raise ValueError
        selected = tuple(kinds)
        if selected not in _PHASE_KINDS:
            raise ValueError
        # Prefer a still-recommended fresh read, without widening what the Core
        # permits. This is opt-in generation guidance, not a coverage policy:
        # the model can repeat a resource or the endpoint can ignore the hint.
        suggestion = context["continuation"].get("suggested_next_action")
        if (selected == ("tool_call", "final") and type(suggestion) is str
                and suggestion == "read_unread_report"):
            return ("tool_call",)
        return selected
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        raise ValueError("invalid_tool_loop_context") from None


def _matches(value, expected):
    # Walk only the finite fixed template, not an arbitrary incoming tree.
    # Exact types prevent bool/int equality or subclasses concealing drift.
    if type(value) is not type(expected):
        return False
    if type(expected) is dict:
        return (len(value) == len(expected) and all(type(key) is str for key in value)
                and set(value) == set(expected) and all(
            _matches(value[key], item) for key, item in expected.items()
        ))
    if type(expected) is list:
        return len(value) == len(expected) and all(
            _matches(item, reference) for item, reference in zip(value, expected, strict=True)
        )
    return value == expected


def tool_loop_format_state(value) -> tuple[str, tuple[str, ...]]:
    """Bind the complete variant, not only the name shared by three schemas."""
    for kinds in _PHASE_KINDS:
        if _matches(value, tool_loop_response_format(kinds)):
            return TOOL_LOOP_SCHEMA_NAME, kinds
    raise ValueError("invalid_chat_response_format")
