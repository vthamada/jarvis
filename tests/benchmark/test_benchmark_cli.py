from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from tools.benchmarks.harness import main


def runtime_dir(name: str) -> Path:
    base_dir = Path(gettempdir()) / "jarvis-tests"
    base_dir.mkdir(parents=True, exist_ok=True)
    target = base_dir / f"{name}-{uuid4().hex[:8]}"
    target.mkdir(parents=True, exist_ok=True)
    return target


def test_benchmark_cli_accepts_output_dir_override(capsys) -> None:
    output_dir = runtime_dir("benchmark-cli") / "benchmarks"

    exit_code = main(["--output-dir", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) >= 2
    assert Path(lines[0]).exists()
    assert Path(lines[1]).exists()
    assert str(output_dir) in lines[0]
