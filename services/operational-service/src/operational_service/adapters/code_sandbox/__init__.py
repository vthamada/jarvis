"""Isolated code fixtures: no arbitrary Python execution or host file access."""

from .fixture import (
    CandidatePatch,
    FixtureCase,
    FixtureCodeSandbox,
    FixtureLimits,
    FixtureRunResult,
    FixtureWorkspace,
    source_digest,
)

__all__ = [
    "CandidatePatch",
    "FixtureCase",
    "FixtureCodeSandbox",
    "FixtureLimits",
    "FixtureRunResult",
    "FixtureWorkspace",
    "source_digest",
]
