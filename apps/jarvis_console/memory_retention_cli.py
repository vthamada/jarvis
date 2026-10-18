"""Advisory retention review of an explicit existing canonical SQLite scope.

No lifecycle mutation, deletion, policy replacement or execution authorization.
The caller's labels bind the read and do not authenticate an operator.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from apps.jarvis_console.bootstrap import ensure_src_paths
from apps.jarvis_console.job_activity_cli import _silence_broken_standard_stream

_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


def _refuse():
    raise ValueError("memory_retention_refused") from None


def _identity(path):
    info = path.lstat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_nlink, info.st_mode)


def build_memory_retention_report(*, authorized=False, database_path: Path, subject_id: str,
                                  session_ids: tuple[str, ...], as_of: str,
                                  max_age_days=30, include_refs=False) -> dict:
    """A complete bounded advisory selection, not canonical retention policy."""
    try:
        if (authorized is not True or type(subject_id) is not str
                or not 1 <= len(subject_id) <= 256
                or type(session_ids) is not tuple or not 1 <= len(session_ids) <= 32
                or any(type(item) is not str or not 1 <= len(item) <= 256 for item in session_ids)
                or len(set(session_ids)) != len(session_ids)
                or type(as_of) is not str or not _STAMP.fullmatch(as_of)
                or type(max_age_days) is not int or not 1 <= max_age_days <= 366
                or type(include_refs) is not bool):
            _refuse()
        now = datetime.fromisoformat(as_of).astimezone(UTC)
        ensure_src_paths()
        from memory_service.readonly_repository import ReadOnlySqliteMemoryRepository
        from memory_service.recall import RecallScope
        from memory_service.retention_review import build_retention_review

        from apps.jarvis_console.recall_cli import _database_path

        path = _database_path(database_path)
        identity = _identity(path)
        deadline = time.monotonic() + 5.0
        repository = ReadOnlySqliteMemoryRepository(
            path, deadline_monotonic=deadline, monotonic_clock=time.monotonic,
        )
        snapshot = repository.fetch_user_scope_snapshot(subject_id)
        if (snapshot is None or snapshot.user_id != subject_id
                or any(session not in snapshot.recent_session_ids for session in session_ids)):
            _refuse()
        rows = []
        for session in session_ids:
            if time.monotonic() >= deadline:
                _refuse()
            if not repository.session_subject_is_compatible(session, subject_id):
                _refuse()
            rows.extend(repository.fetch_recent_turns(session, 101))
            if len(rows) > 100:
                _refuse()
        plan = build_retention_review(
            rows, scope=RecallScope(subject_id, session_ids, now),
            max_candidates=100, max_age_seconds=max_age_days * 86400,
            deadline_monotonic=deadline, monotonic_clock=time.monotonic,
        )
        if plan.status not in {"review_ready", "empty", "needs_decision"}:
            _refuse()
        result = plan.metadata(include_refs=include_refs)
        # Read membership is not an OS identity or Core grant. Do not silently
        # truncate history into a purported complete plan for the selected scope.
        result.update({"schema_version": "jarvis-memory-retention-review-v1",
                       "source_mode": "quiescent_existing_canonical_sqlite",
                       "scope_binding": "caller_supplied_not_authentication",
                       "operator_authenticated": False,
                       "selection_scope": "explicit_sessions_bounded_not_entire_memory",
                       "source_states_mode": "default_no_declared_lifecycle_overrides"})
        rendered = json.dumps(result, ensure_ascii=True, allow_nan=False)
        if len(rendered.encode("ascii")) > 65536:
            _refuse()
        repository._require_quiescent_database()
        _database_path(path)
        if time.monotonic() >= deadline or _identity(path) != identity:
            _refuse()
        return json.loads(rendered)
    except Exception:
        _refuse()


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        _refuse()


def main(argv=None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--memory-db", type=Path)
    parser.add_argument("--subject-id")
    parser.add_argument("--session-id", action="append")
    parser.add_argument("--as-of")
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--include-refs", action="store_true")
    try:
        args = parser.parse_args(argv)
        result = build_memory_retention_report(
            authorized=args.authorized, database_path=args.memory_db, subject_id=args.subject_id,
            session_ids=tuple(args.session_id or ()), as_of=args.as_of,
            max_age_days=args.max_age_days, include_refs=args.include_refs,
        )
        print(json.dumps(result, ensure_ascii=True, allow_nan=False), flush=True)
        return 0
    except (Exception, KeyboardInterrupt):
        try:
            print('{"error_code": "memory_retention_refused"}', file=sys.stderr, flush=True)
        except (OSError, UnicodeError, ValueError):
            _silence_broken_standard_stream(sys.stderr, 2)
        _silence_broken_standard_stream(sys.stdout, 1)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
