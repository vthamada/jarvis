"""Explicit local, read-only canonical recall inspection; no authentication claim."""

from __future__ import annotations

import json
import stat
import time
import unicodedata
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

from memory_service.readonly_repository import ReadOnlySqliteMemoryRepository
from memory_service.recall import RecallLimits, RecallScope, select_readonly_recall

from apps.jarvis_console.registry import CommandExecutionResult
from apps.jarvis_console.runtime import ConsoleCommandError, ConsoleExitCode

MAX_DATABASE_BYTES = 128 * 1024 * 1024


def _refuse() -> None:
    raise ConsoleCommandError(
        "Memory recall refused: verify explicit scope and a quiescent local database.",
        error_code="memory_recall_refused", exit_code=ConsoleExitCode.GOVERNANCE_BLOCKED,
    )


def _database_path(value: object) -> Path:
    if not isinstance(value, (str, Path)):
        _refuse()
    path = Path(value)
    if (not path.is_absolute() or ".." in path.parts
            or str(path).startswith("\\\\")):
        _refuse()
    # Preflight only: this is not an anti-race descriptor walk or filesystem sandbox.
    for component in (path, *path.parents):
        info = component.lstat()
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400):
            _refuse()
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or not 100 <= info.st_size <= MAX_DATABASE_BYTES
            or getattr(info, "st_nlink", 1) != 1):
        _refuse()
    return path


def _safe_text(value: object) -> str:
    text = str(value)
    # Escape terminal controls (including bidi format chars); content stays data.
    return "".join(
        f"\\u{ord(char):04x}" if (
            unicodedata.category(char).startswith("C")
            or unicodedata.category(char) in {"Zl", "Zp"}
        ) else char
        for char in text
    )


def run_memory_recall(args: Namespace) -> CommandExecutionResult:
    try:
        path = _database_path(args.memory_db)
        sessions = tuple(args.session_id)
        if (not isinstance(args.subject_id, str) or not 1 <= len(args.subject_id) <= 256
                or not 1 <= len(sessions) <= 32 or len(set(sessions)) != len(sessions)
                or any(not isinstance(s, str) or not 1 <= len(s) <= 256 for s in sessions)
                or not isinstance(args.query, str) or not 1 <= len(args.query) <= 2048
                or type(args.limit) is not int or not 1 <= args.limit <= 32):
            _refuse()
        repository = ReadOnlySqliteMemoryRepository(path)
        snapshot = repository.fetch_user_scope_snapshot(args.subject_id)
        if (snapshot is None or snapshot.user_id != args.subject_id
                or any(session not in snapshot.recent_session_ids for session in sessions)):
            _refuse()
        # Snapshot membership is not ownership: inspect whole persisted session history.
        for session in sessions:
            if not repository.session_subject_is_compatible(session, args.subject_id):
                _refuse()
        limits = RecallLimits(max_items=args.limit, deadline_monotonic=time.monotonic() + 2)
        rows = []
        for session in sessions:
            rows.extend(repository.fetch_recent_turns(session, limits.max_candidates + 1))
            if len(rows) > limits.max_candidates:
                _refuse()
        selection = select_readonly_recall(
            rows, scope=RecallScope(args.subject_id, sessions, datetime.now(timezone.utc)),
            query=args.query, limits=limits,
        )
        if selection.status not in {"selected", "no_match", "needs_decision"}:
            _refuse()
        include_content = bool(args.include_content)
        items = []
        for item in selection.items:
            projected = {
                "source_ref": item.source_ref, "age_seconds": item.age_seconds,
                "reasons": item.reasons, "version": item.version,
                "truncated": item.truncated, "content_role": item.content_role,
            }
            if include_content:
                projected["request_content"] = item.request_content
                projected["response_text"] = item.response_text
            items.append(projected)
        payload = {
            "schema_version": "jarvis-memory-recall/v1", "status": selection.status,
            "selector": selection.selector, "authority": selection.authority,
            "contains_content": include_content, "selected_count": len(items),
            "inspected_count": selection.inspected_count,
            "exclusions": dict(selection.exclusions), "items": items,
        }
        if args.output_format == "json":
            output = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        else:
            lines = [f"memory-recall status={selection.status} authority=none",
                     f"selected={len(items)} inspected={selection.inspected_count} "
                     f"contains_content={str(include_content).lower()}"]
            for item in items:
                lines.append(f"source_ref={item['source_ref']} age_seconds={item['age_seconds']}")
                if include_content:
                    lines.append("request_content=" + _safe_text(item["request_content"]))
                    lines.append("response_text=" + _safe_text(item["response_text"]))
            output = "\n".join(lines)
        return CommandExecutionResult(outputs=[output])
    except ConsoleCommandError:
        raise
    except Exception:
        # No SQL, paths, subject ids, query, exception messages or argv echo.
        _refuse()
