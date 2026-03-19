from pathlib import Path

from tools.benchmarks.harness import main


def test_benchmark_cli_accepts_output_dir_override(tmp_path: Path, capsys) -> None:
    output_dir = tmp_path / "benchmarks"

    exit_code = main(["--output-dir", str(output_dir)])

    captured = capsys.readouterr()
    assert exit_code == 0
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert len(lines) >= 2
    assert Path(lines[0]).exists()
    assert Path(lines[1]).exists()
    assert str(output_dir) in lines[0]
