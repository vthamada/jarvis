from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from tools.benchmarks.harness import (
    ADOPT_IN_V1,
    DEFER_TO_V2,
    MAINTAIN_BASELINE,
    BenchmarkHarness,
)


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_benchmark_harness_runs_and_persists_auditable_outputs(monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    harness = BenchmarkHarness(output_dir=str(runtime_dir("benchmark-harness") / "benchmarks"))

    report = harness.run()

    assert Path(report.json_report_path).exists()
    assert Path(report.markdown_report_path).exists()
    allowed_decisions = {ADOPT_IN_V1, MAINTAIN_BASELINE, DEFER_TO_V2}
    assert all(track.decision in allowed_decisions for track in report.tracks.values())
    assert report.tracks["memory"].decision == MAINTAIN_BASELINE
    assert report.tracks["knowledge"].decision == ADOPT_IN_V1
    assert report.tracks["observability"].decision == ADOPT_IN_V1
    assert report.tracks["evolution"].decision == ADOPT_IN_V1
