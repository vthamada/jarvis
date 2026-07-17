"""Run a versioned offline domain eval pack and persist bounded evidence."""
# ruff: noqa: E402

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from dataclasses import asdict
from json import dumps
from pathlib import Path
from sys import path as sys_path
from time import time

ROOT = Path(__file__).resolve().parent.parent
sys_path.insert(0, str(ROOT))

from tools.domain_eval_support import DEFAULT_DOMAIN_EVAL_PACK_PATH, run_domain_eval_pack


def parse_args() -> Namespace:
    parser = ArgumentParser(description="Run a governed offline JARVIS domain eval pack.")
    parser.add_argument("--pack", default=str(DEFAULT_DOMAIN_EVAL_PACK_PATH))
    parser.add_argument("--profile", choices=["development", "controlled"], default="development")
    parser.add_argument("--output-dir")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser.parse_args()


def render_text(payload: dict[str, object]) -> str:
    lines = [
        " ".join(
            [
                f"run_id={payload['run_id']}",
                f"eval_pack_id={payload['eval_pack_id']}",
                f"route={payload['route_name']}",
                f"status={payload['status']}",
                f"readiness={payload['readiness_status']}",
                f"pass_rate={payload['pass_rate']}",
                f"promotion_readiness={payload['promotion_readiness']}",
            ]
        )
    ]
    for result in payload["case_results"]:
        lines.append(
            " ".join(
                [
                    f"case_id={result['case_id']}",
                    f"passed={str(result['passed']).lower()}",
                    f"decision={result['observed_governance_decision'] or 'none'}",
                    f"route={result['observed_route'] or 'none'}",
                    f"workflow={result['observed_workflow_profile'] or 'none'}",
                    f"memory={result['observed_memory_causality_status']}",
                    f"failures={','.join(result['failures']) or 'none'}",
                ]
            )
        )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    run_id = f"domain-eval-{int(time())}"
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else ROOT / ".jarvis_runtime" / "domain_evals" / run_id
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_domain_eval_pack(
        pack_path=args.pack,
        profile=args.profile,
        workdir=output_dir,
        run_id=run_id,
    )
    payload = asdict(result)
    json_text = dumps(payload, ensure_ascii=True, indent=2)
    text = render_text(payload)
    (output_dir / "domain_eval_results.json").write_text(json_text, encoding="utf-8")
    (output_dir / "domain_eval_results.md").write_text(text, encoding="utf-8")
    print(json_text if args.format == "json" else text)
    return 0 if result.status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
