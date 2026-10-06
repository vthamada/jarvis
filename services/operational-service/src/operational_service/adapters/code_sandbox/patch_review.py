"""Bounded, untrusted code proposals for review; never application or execution.

Only existing, explicitly allowlisted in-memory files can be changed. Neither
hashes nor successful preview verification constitute authority or test evidence.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field

_SEGMENT = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_RESERVED = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
_RESERVED.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10))


class _Rejected(Exception):
    pass


def text_sha256(text: str) -> str:
    """Exact UTF-8 fingerprint, not a trust assertion."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fingerprint(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class ReviewLimits:
    max_files: int = 32
    max_changed_files: int = 8
    max_file_bytes: int = 16384
    max_total_bytes: int = 131072
    max_edits: int = 32
    max_lines_per_file: int = 512
    max_diff_bytes: int = 131072
    max_diff_hunks: int = 64

    def __post_init__(self) -> None:
        ceilings = {
            "max_files": 64,
            "max_changed_files": 16,
            "max_file_bytes": 32768,
            "max_total_bytes": 262144,
            "max_edits": 64,
            "max_lines_per_file": 1024,
            "max_diff_bytes": 262144,
            "max_diff_hunks": 128,
        }
        if any(
            type(getattr(self, key)) is not int or not 1 <= getattr(self, key) <= ceiling
            for key, ceiling in ceilings.items()
        ):
            raise ValueError("invalid_review_limits")


@dataclass(frozen=True)
class SnapshotFile:
    path: str = field(repr=False)
    text: str = field(repr=False)


@dataclass(frozen=True)
class ReviewSnapshot:
    files: tuple[SnapshotFile, ...] = field(repr=False)
    sha256: str


@dataclass(frozen=True)
class TextEdit:
    """Offsets count Python characters in the exact, unnormalized preimage.

    A span must replace at least one original character. Span removal is allowed;
    inserting a new file, emptying a file, rename and deletion are not operations.
    """

    start: int
    end: int
    expected_text: str = field(repr=False)
    replacement: str = field(repr=False)


@dataclass(frozen=True)
class FileEdits:
    path: str = field(repr=False)
    expected_sha256: str
    edits: tuple[TextEdit, ...] = field(repr=False)


@dataclass(frozen=True)
class PatchProposal:
    expected_snapshot_sha256: str
    files: tuple[FileEdits, ...] = field(repr=False)


@dataclass(frozen=True)
class FileSummary:
    path: str = field(repr=False)
    before_sha256: str
    after_sha256: str
    edits: int
    added_lines: int
    removed_lines: int
    diff_hunks: int


@dataclass(frozen=True)
class PatchPreview:
    status: str
    reason: str
    proposal_sha256: str | None = None
    preview_sha256: str | None = None
    base_sha256: str | None = None
    candidate_sha256: str | None = None
    summaries: tuple[FileSummary, ...] = field(default=(), repr=False)
    diff: str = field(default="", repr=False)
    candidate: ReviewSnapshot | None = field(default=None, repr=False)
    proposal: PatchProposal | None = field(default=None, repr=False)
    evidence_mode: str = "in_memory_preview"
    host_effects: bool = False
    tests_executed: bool = False
    authority_granted: bool = False

    def telemetry(self) -> dict[str, str | int | bool | None]:
        """Content-free projection; source, paths and diffs need explicit access."""
        return {
            "status": self.status,
            "reason": self.reason,
            "proposal_sha256": self.proposal_sha256,
            "preview_sha256": self.preview_sha256,
            "base_sha256": self.base_sha256,
            "candidate_sha256": self.candidate_sha256,
            "changed_files": len(self.summaries),
            "edits": sum(item.edits for item in self.summaries),
            "diff_hunks": sum(item.diff_hunks for item in self.summaries),
            "evidence_mode": self.evidence_mode,
            "host_effects": self.host_effects,
            "tests_executed": self.tests_executed,
            "authority_granted": self.authority_granted,
        }


class PatchReviewer:
    """Pure candidate review over bounded snapshots, without runtime adapters.

    The trusted caller selects the finite allowlist. Candidate content remains
    untrusted, including text that resembles instructions, grants or commands.
    """

    def __init__(self, allowed_paths: tuple[str, ...], limits: ReviewLimits | None = None):
        if limits is not None and type(limits) is not ReviewLimits:
            raise ValueError("invalid_review_limits")
        self.limits = limits or ReviewLimits()
        if type(allowed_paths) is not tuple or not 1 <= len(allowed_paths) <= 64:
            raise ValueError("invalid_review_allowlist")
        try:
            for path in allowed_paths:
                self._path(path)
            if len({path.casefold() for path in allowed_paths}) != len(allowed_paths):
                raise _Rejected("duplicate_path")
        except _Rejected:
            raise ValueError("invalid_review_allowlist") from None
        self._allowed_paths = frozenset(allowed_paths)

    @staticmethod
    def _path(path: str) -> None:
        if type(path) is not str or not 1 <= len(path) <= 180:
            raise _Rejected("invalid_path")
        for part in path.split("/"):
            if (
                not _SEGMENT.fullmatch(part)
                or part in (".", "..")
                or part.endswith(".")
                or part.split(".", 1)[0].upper() in _RESERVED
            ):
                raise _Rejected("invalid_path")

    def _text(self, text: str, *, allow_empty: bool = False) -> None:
        if type(text) is not str or len(text) > self.limits.max_file_bytes:
            raise _Rejected("content_limit")
        if not text and not allow_empty:
            raise _Rejected("empty_file_not_supported")
        # Reject invisible/bidi/control payloads in review output, not executable syntax.
        if any(
            (unicodedata.category(char).startswith("C") and char not in "\n\t")
            or char in "\u2028\u2029"
            for char in text
        ):
            raise _Rejected("unsafe_text_control")
        if len(text.encode("utf-8")) > self.limits.max_file_bytes:
            raise _Rejected("content_limit")
        if text.count("\n") + 1 > self.limits.max_lines_per_file:
            raise _Rejected("line_limit")

    def _snapshot_files(self, snapshot: ReviewSnapshot) -> dict[str, str]:
        if (
            type(snapshot) is not ReviewSnapshot
            or type(snapshot.files) is not tuple
            or not 1 <= len(snapshot.files) <= self.limits.max_files
        ):
            raise _Rejected("invalid_snapshot")
        files = {}
        folded = set()
        total = 0
        for item in snapshot.files:
            if type(item) is not SnapshotFile:
                raise _Rejected("invalid_snapshot")
            self._path(item.path)
            if item.path.casefold() in folded:
                raise _Rejected("duplicate_path")
            folded.add(item.path.casefold())
            self._text(item.text)
            files[item.path] = item.text
            total += len(item.text.encode("utf-8"))
            if total > self.limits.max_total_bytes:
                raise _Rejected("total_content_limit")
        if (
            type(snapshot.sha256) is not str
            or not _HASH.fullmatch(snapshot.sha256)
            or snapshot.sha256 != self._snapshot_digest(files)
        ):
            raise _Rejected("snapshot_tampered")
        return files

    @staticmethod
    def _snapshot_digest(files: dict[str, str]) -> str:
        return _fingerprint([[path, text_sha256(files[path])] for path in sorted(files)])

    def snapshot(self, sources: dict[str, str]) -> ReviewSnapshot:
        """Copy a finite fixture dictionary; invalid inputs raise sanitized ValueError."""
        try:
            if type(sources) is not dict or not 1 <= len(sources) <= self.limits.max_files:
                raise _Rejected("invalid_snapshot")
            # Validate before sorting/hashing; candidates cannot supply comparison objects.
            for path, text in sources.items():
                self._path(path)
                self._text(text)
            result = ReviewSnapshot(
                tuple(SnapshotFile(path, sources[path]) for path in sorted(sources)),
                self._snapshot_digest(sources),
            )
            self._snapshot_files(result)
            return result
        except _Rejected as exc:
            raise ValueError(str(exc)) from None

    def preview(self, snapshot: ReviewSnapshot, proposal: PatchProposal) -> PatchPreview:
        """Recompute exact spans from the original snapshot, without side effects."""
        try:
            original = self._snapshot_files(snapshot)
            if (
                type(proposal) is not PatchProposal
                or type(proposal.files) is not tuple
                or not 1 <= len(proposal.files) <= self.limits.max_changed_files
            ):
                raise _Rejected("invalid_proposal")
            if (
                type(proposal.expected_snapshot_sha256) is not str
                or not _HASH.fullmatch(proposal.expected_snapshot_sha256)
                or proposal.expected_snapshot_sha256 != snapshot.sha256
            ):
                raise _Rejected("snapshot_conflict")
            candidate = dict(original)
            changes = []
            seen = set()
            edit_count = 0
            for change in proposal.files:
                if type(change) is not FileEdits:
                    raise _Rejected("invalid_file_edits")
                self._path(change.path)
                if change.path in seen:
                    raise _Rejected("duplicate_file_edits")
                seen.add(change.path)
                if change.path not in self._allowed_paths:
                    raise _Rejected("path_not_allowlisted")
                if change.path not in original:
                    raise _Rejected("file_creation_not_supported")
                before = original[change.path]
                if (
                    type(change.expected_sha256) is not str
                    or not _HASH.fullmatch(change.expected_sha256)
                    or change.expected_sha256 != text_sha256(before)
                ):
                    raise _Rejected("preimage_conflict")
                if type(change.edits) is not tuple or not change.edits:
                    raise _Rejected("invalid_edits")
                edit_count += len(change.edits)
                if edit_count > self.limits.max_edits:
                    raise _Rejected("edit_limit")
                offset = 0
                parts = []
                spans = []
                for edit in change.edits:
                    if type(edit) is not TextEdit:
                        raise _Rejected("invalid_edit")
                    if (
                        type(edit.start) is not int
                        or type(edit.end) is not int
                        or not offset <= edit.start < edit.end <= len(before)
                    ):
                        raise _Rejected("invalid_edit_span")
                    self._text(edit.expected_text)
                    self._text(edit.replacement, allow_empty=True)
                    if before[edit.start : edit.end] != edit.expected_text:
                        raise _Rejected("span_preimage_conflict")
                    if edit.expected_text == edit.replacement:
                        raise _Rejected("no_change")
                    parts.extend((before[offset : edit.start], edit.replacement))
                    offset = edit.end
                    spans.append([edit.start, edit.end, edit.expected_text, edit.replacement])
                parts.append(before[offset:])
                after = "".join(parts)
                self._text(after)
                if after == before:
                    raise _Rejected("no_change")
                candidate[change.path] = after
                changes.append([change.path, change.expected_sha256, spans])
            candidate_snapshot = self.snapshot(candidate)
            # File order is canonical; edit order is the exact preimage offset order.
            changes.sort(key=lambda item: item[0])
            proposal_hash = _fingerprint(["patch_review.v1", snapshot.sha256, changes])
            summaries = []
            chunks = []
            diff_size = 0
            total_hunks = 0
            for path, before_hash, spans in changes:
                # split on LF only: other Unicode characters cannot fake diff delimiters.
                def lines(text: str) -> list[str]:
                    raw = text.split("\n")
                    return [line + "\n" for line in raw[:-1]] + ([raw[-1]] if raw[-1] else [])

                raw_diff = list(
                    difflib.unified_diff(
                        lines(original[path]),
                        lines(candidate[path]),
                        fromfile=f"before/{path}",
                        tofile=f"candidate/{path}",
                        n=3,
                    )
                )
                # Keep the conventional no-newline marker; otherwise adjacent lines lie.
                rendered = "".join(
                    line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                    for line in raw_diff
                )
                added = sum(line.startswith("+") for line in raw_diff[2:])
                removed = sum(line.startswith("-") for line in raw_diff[2:])
                hunks = sum(line.startswith("@@ ") for line in raw_diff)
                total_hunks += hunks
                diff_size += len(rendered.encode("utf-8"))
                if (
                    diff_size > self.limits.max_diff_bytes
                    or total_hunks > self.limits.max_diff_hunks
                ):
                    raise _Rejected("diff_limit")
                chunks.append(rendered)
                summaries.append(
                    FileSummary(
                        path,
                        before_hash,
                        text_sha256(candidate[path]),
                        len(spans),
                        added,
                        removed,
                        hunks,
                    )
                )
            diff = "".join(chunks)
            preview_hash = _fingerprint(
                [
                    "patch_preview.v1",
                    proposal_hash,
                    snapshot.sha256,
                    candidate_snapshot.sha256,
                    text_sha256(diff),
                    [
                        [
                            item.path,
                            item.before_sha256,
                            item.after_sha256,
                            item.edits,
                            item.added_lines,
                            item.removed_lines,
                            item.diff_hunks,
                        ]
                        for item in summaries
                    ],
                ]
            )
            return PatchPreview(
                "reviewable",
                "preview_only",
                proposal_hash,
                preview_hash,
                snapshot.sha256,
                candidate_snapshot.sha256,
                tuple(summaries),
                diff,
                candidate_snapshot,
                proposal,
            )
        except (_Rejected, ValueError) as exc:
            # snapshot() only emits sanitized error codes; never include candidate content.
            return PatchPreview("rejected", str(exc))

    def verify(
        self,
        preview: PatchPreview,
        current_snapshot: ReviewSnapshot,
        *,
        expected_proposal_sha256: str,
    ) -> PatchPreview:
        """Detect stale input/tampering at review time, without approving application."""
        if (
            type(preview) is not PatchPreview
            or preview.status != "reviewable"
            or type(expected_proposal_sha256) is not str
            or not _HASH.fullmatch(expected_proposal_sha256)
            or preview.proposal_sha256 != expected_proposal_sha256
        ):
            return PatchPreview("rejected", "review_binding_conflict")
        # Dataclasses are the wire contract, not intrinsically trusted objects.
        if (
            any(
                type(getattr(preview, name)) is not str
                for name in (
                    "reason",
                    "proposal_sha256",
                    "preview_sha256",
                    "base_sha256",
                    "candidate_sha256",
                    "diff",
                    "evidence_mode",
                )
            )
            or any(
                type(getattr(preview, name)) is not bool
                for name in ("host_effects", "tests_executed", "authority_granted")
            )
            or type(preview.summaries) is not tuple
            or len(preview.summaries) > self.limits.max_changed_files
            or type(preview.candidate) is not ReviewSnapshot
        ):
            return PatchPreview("rejected", "preview_tampered")
        if len(preview.diff) > self.limits.max_diff_bytes:
            return PatchPreview("rejected", "preview_tampered")
        for item in preview.summaries:
            if (
                type(item) is not FileSummary
                or any(
                    type(getattr(item, name)) is not str
                    for name in ("path", "before_sha256", "after_sha256")
                )
                or any(
                    type(getattr(item, name)) is not int
                    for name in ("edits", "added_lines", "removed_lines", "diff_hunks")
                )
            ):
                return PatchPreview("rejected", "preview_tampered")
        try:
            self._snapshot_files(preview.candidate)
        except _Rejected:
            return PatchPreview("rejected", "preview_tampered")
        recomputed = self.preview(current_snapshot, preview.proposal)
        if recomputed.status != "reviewable":
            return recomputed
        if recomputed != preview:
            return PatchPreview("rejected", "preview_tampered")
        return recomputed
