"""A bounded arithmetic fixture interpreter, NOT an operating-system sandbox.

Candidate source is data. Only explicitly supported AST nodes are interpreted;
Python execution, imports, calls, host filesystem and network are unavailable.
Passing here is fixture evidence, never an authorization to apply a real patch.
"""

from __future__ import annotations

import ast
import difflib
import hashlib
import math
import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

_RESERVED = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
_RESERVED.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10))
_SEGMENT = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z")
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*\Z")


class _Rejected(Exception):
    pass


class _Stopped(Exception):
    pass


def source_digest(source: str) -> str:
    """Content fingerprint for optimistic patch matching, not a trust assertion."""
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _validate_path(path: str) -> None:
    if type(path) is not str or len(path) > 240:
        raise _Rejected("invalid_path")
    parts = path.split("/")
    for part in parts:
        if (
            not _SEGMENT.fullmatch(part)
            or part in (".", "..")
            or part.endswith((".", " "))
            or part.split(".", 1)[0].upper() in _RESERVED
        ):
            raise _Rejected("invalid_path")
    if not path.endswith(".py"):
        raise _Rejected("invalid_path")


@dataclass(frozen=True)
class FixtureLimits:
    max_files: int = 16
    max_source_chars: int = 8192
    max_total_chars: int = 32768
    max_patches: int = 16
    max_cases: int = 64
    max_ast_nodes: int = 256
    max_ast_depth: int = 32
    max_integer_bits: int = 64
    max_arguments: int = 8
    timeout_seconds: float = 1.0

    def __post_init__(self) -> None:
        hard_bounds = {
            "max_files": 128,
            "max_source_chars": 32768,
            "max_total_chars": 131072,
            "max_patches": 128,
            "max_cases": 256,
            "max_ast_nodes": 1024,
            "max_ast_depth": 64,
            "max_integer_bits": 128,
            "max_arguments": 16,
        }
        for name, ceiling in hard_bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError("invalid_fixture_limits")
        if type(self.timeout_seconds) not in (int, float) or not 0 < self.timeout_seconds <= 5:
            raise ValueError("invalid_fixture_limits")


@dataclass(frozen=True)
class CandidatePatch:
    path: str = field(repr=False)
    before_text: str = field(repr=False)
    after_text: str = field(repr=False)
    expected_sha256: str = field(repr=False)


@dataclass(frozen=True)
class FixtureCase:
    path: str = field(repr=False)
    function: str = field(repr=False)
    arguments: tuple[int, ...] = field(repr=False)
    expected: int = field(repr=False)


@dataclass(frozen=True)
class FixtureWorkspace:
    sources: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        # Copy even a mutable caller mapping: patching cannot affect its owner.
        object.__setattr__(self, "sources", MappingProxyType(dict(self.sources)))


@dataclass(frozen=True)
class FixtureRunResult:
    status: str
    reason: str
    tested: int
    passed: int
    failed: int
    candidate_sha256: str | None
    diff: str = field(default="", repr=False)
    workspace: FixtureWorkspace | None = field(default=None, repr=False)
    evidence_mode: str = "fixture"
    model_generated: bool = False
    host_effects: bool = False

    def telemetry(self) -> dict[str, str | int | bool | None]:
        """Allowlisted content-free operational projection."""
        return {
            "status": self.status,
            "reason": self.reason,
            "tested": self.tested,
            "passed": self.passed,
            "failed": self.failed,
            "candidate_sha256": self.candidate_sha256,
            "evidence_mode": self.evidence_mode,
            "model_generated": self.model_generated,
            "host_effects": self.host_effects,
        }


def _integer(value: object, limits: FixtureLimits) -> int:
    if type(value) is not int or value.bit_length() > limits.max_integer_bits:
        raise _Rejected("integer_limit")
    return value


def _expression(
    node: ast.expr, values: Mapping[str, int], limits: FixtureLimits, check: Callable[[], None]
) -> int:
    check()
    if isinstance(node, ast.Constant):
        return _integer(node.value, limits)
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _expression(node.operand, values, limits, check)
        return _integer(value if isinstance(node.op, ast.UAdd) else -value, limits)
    if isinstance(node, ast.BinOp):
        left = _expression(node.left, values, limits, check)
        right = _expression(node.right, values, limits, check)
        if isinstance(node.op, ast.Add):
            value = left + right
        elif isinstance(node.op, ast.Sub):
            value = left - right
        elif isinstance(node.op, ast.Mult):
            value = left * right
        elif isinstance(node.op, (ast.FloorDiv, ast.Mod)):
            if not right:
                raise _Rejected("arithmetic_error")
            value = left // right if isinstance(node.op, ast.FloorDiv) else left % right
        else:
            raise _Rejected("unsupported_syntax")
        return _integer(value, limits)
    raise _Rejected("unsupported_syntax")


def _parse_source(source: str, limits: FixtureLimits, check: Callable[[], None]):
    check()
    try:
        module = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        raise _Rejected("invalid_source") from None
    nodes = [(module, 0)]
    count = 0
    allowed = (
        ast.Module,
        ast.FunctionDef,
        ast.arguments,
        ast.arg,
        ast.Return,
        ast.BinOp,
        ast.UnaryOp,
        ast.Name,
        ast.Load,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.FloorDiv,
        ast.Mod,
        ast.UAdd,
        ast.USub,
    )
    while nodes:
        check()
        node, depth = nodes.pop()
        count += 1
        if count > limits.max_ast_nodes or depth > limits.max_ast_depth:
            raise _Rejected("ast_limit")
        if not isinstance(node, allowed):
            raise _Rejected("unsupported_syntax")
        if isinstance(node, ast.Constant):
            _integer(node.value, limits)
        nodes.extend((child, depth + 1) for child in ast.iter_child_nodes(node))
    functions = {}
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            raise _Rejected("unsupported_syntax")
        args = node.args
        arguments = args.posonlyargs + args.args
        if (
            not _IDENTIFIER.fullmatch(node.name)
            or node.name in functions
            or node.decorator_list
            or node.returns
            or node.type_comment
            or args.vararg
            or args.kwarg
            or args.kwonlyargs
            or args.defaults
            or len(arguments) > limits.max_arguments
            or any(arg.annotation or not _IDENTIFIER.fullmatch(arg.arg) for arg in arguments)
            or len({arg.arg for arg in arguments}) != len(arguments)
            or len(node.body) != 1
            or not isinstance(node.body[0], ast.Return)
            or node.body[0].value is None
        ):
            raise _Rejected("unsupported_syntax")
        names = {arg.arg for arg in arguments}
        if any(isinstance(child, ast.Name) and child.id not in names for child in ast.walk(node)):
            raise _Rejected("unsupported_syntax")
        functions[node.name] = (tuple(arg.arg for arg in arguments), node.body[0].value)
    if not functions:
        raise _Rejected("unsupported_syntax")
    check()
    return functions


class FixtureCodeSandbox:
    """Patch and test a copied mapping using the small interpreter above.

    No Core, authority receipt, filesystem adapter or model provider is wired.
    Deadline/cancel callbacks are trusted harness controls, not candidate code.
    """

    def __init__(self, limits: FixtureLimits | None = None):
        if limits is not None and type(limits) is not FixtureLimits:
            raise ValueError("invalid_fixture_limits")
        self.limits = limits or FixtureLimits()

    def run(
        self,
        workspace: FixtureWorkspace,
        patches: Sequence[CandidatePatch],
        cases: Sequence[FixtureCase],
        *,
        cancelled: Callable[[], bool] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> FixtureRunResult:
        tested = passed = failed = 0
        digest = None
        previous_clock = None

        def read_clock() -> float:
            nonlocal previous_clock
            try:
                value = clock()
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise _Rejected("invalid_clock")
            except _Rejected:
                raise
            except Exception:
                raise _Rejected("control_error") from None
            if previous_clock is not None and value < previous_clock:
                raise _Rejected("invalid_clock")
            previous_clock = value
            return value

        def check() -> None:
            if cancelled is not None:
                try:
                    cancellation = cancelled()
                except Exception:
                    raise _Rejected("control_error") from None
                if type(cancellation) is not bool:
                    raise _Rejected("control_error")
                if cancellation:
                    raise _Stopped("cancelled")
            if read_clock() - started >= self.limits.timeout_seconds:
                raise _Stopped("timed_out")

        try:
            started = read_clock()
            check()
            limits = self.limits
            if not isinstance(workspace, FixtureWorkspace):
                raise _Rejected("invalid_workspace")
            if type(patches) not in (list, tuple) or type(cases) not in (list, tuple):
                raise _Rejected("invalid_collection")
            if not 1 <= len(workspace.sources) <= limits.max_files:
                raise _Rejected("file_limit")
            if len(patches) > limits.max_patches or not 1 <= len(cases) <= limits.max_cases:
                raise _Rejected("case_or_patch_limit")
            candidate = dict(workspace.sources)
            total = 0
            canonical_paths = set()
            for path, source in candidate.items():
                check()
                _validate_path(path)
                if path.casefold() in canonical_paths:
                    raise _Rejected("duplicate_path")
                canonical_paths.add(path.casefold())
                if type(source) is not str or len(source) > limits.max_source_chars:
                    raise _Rejected("source_limit")
                try:
                    source.encode("utf-8")
                except UnicodeEncodeError:
                    raise _Rejected("invalid_source") from None
                total += len(source)
            if total > limits.max_total_chars:
                raise _Rejected("source_limit")
            seen = set()
            for patch in patches:
                check()
                if not isinstance(patch, CandidatePatch):
                    raise _Rejected("invalid_patch")
                _validate_path(patch.path)
                if patch.path.casefold() in seen:
                    raise _Rejected("duplicate_patch")
                seen.add(patch.path.casefold())
                if patch.path not in candidate:
                    raise _Rejected("unknown_path")
                current = candidate[patch.path]
                if (
                    type(patch.before_text) is not str
                    or type(patch.after_text) is not str
                    or len(patch.before_text) > limits.max_source_chars
                    or len(patch.after_text) > limits.max_source_chars
                ):
                    raise _Rejected("source_limit")
                if patch.before_text != current or patch.expected_sha256 != source_digest(current):
                    raise _Rejected("patch_conflict")
                try:
                    patch.after_text.encode("utf-8")
                except UnicodeEncodeError:
                    raise _Rejected("invalid_source") from None
                total += len(patch.after_text) - len(current)
                if total > limits.max_total_chars:
                    raise _Rejected("source_limit")
                candidate[patch.path] = patch.after_text
            # All files are checked, including files not mentioned by test cases.
            parsed = {
                path: _parse_source(source, limits, check) for path, source in candidate.items()
            }
            fingerprint = hashlib.sha256()
            for path in sorted(candidate):
                fingerprint.update(path.encode("utf-8") + b"\0")
                fingerprint.update(source_digest(candidate[path]).encode("ascii") + b"\0")
            digest = fingerprint.hexdigest()
            for case in cases:
                check()
                if not isinstance(case, FixtureCase):
                    raise _Rejected("invalid_case")
                _validate_path(case.path)
                if (
                    case.path not in parsed
                    or type(case.function) is not str
                    or case.function not in parsed[case.path]
                ):
                    raise _Rejected("unknown_function")
                if type(case.arguments) is not tuple or len(case.arguments) > limits.max_arguments:
                    raise _Rejected("invalid_arguments")
                expected = _integer(case.expected, limits)
                names, expression = parsed[case.path][case.function]
                if len(names) != len(case.arguments):
                    raise _Rejected("invalid_arguments")
                values = {
                    name: _integer(value, limits) for name, value in zip(names, case.arguments)
                }
                actual = _expression(expression, values, limits, check)
                tested += 1
                passed += int(actual == expected)
                failed += int(actual != expected)
            check()
            diff = "".join(
                "".join(
                    difflib.unified_diff(
                        workspace.sources[patch.path].splitlines(keepends=True),
                        candidate[patch.path].splitlines(keepends=True),
                        fromfile=f"before/{patch.path}",
                        tofile=f"candidate/{patch.path}",
                    )
                )
                for patch in patches
            )
            check()
            status = "passed" if not failed else "test_failed"
            return FixtureRunResult(
                status,
                "completed",
                tested,
                passed,
                failed,
                digest,
                diff=diff,
                workspace=FixtureWorkspace(candidate),
            )
        except _Stopped as exc:
            return FixtureRunResult(str(exc), str(exc), tested, passed, failed, digest)
        except _Rejected as exc:
            return FixtureRunResult("rejected", str(exc), tested, passed, failed, digest)
