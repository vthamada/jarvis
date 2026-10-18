"""Explicit stdin-only local comparison; untrusted text never becomes authority."""

from __future__ import annotations

import argparse
import json
import sys
from argparse import Namespace

from apps.jarvis_console.bootstrap import ensure_src_paths
from apps.jarvis_console.job_activity_cli import _silence_broken_standard_stream
from apps.jarvis_console.review_input import run_review_product


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise ValueError("source_comparison_refused") from None


def main(argv=None) -> int:
    parser = _Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--include-content", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.authorized is not True:
            raise ValueError("source_comparison_refused")
        ensure_src_paths()
        from knowledge_service.source_comparison import build_source_comparison

        result = run_review_product(Namespace(include_content=args.include_content),
                                    build_source_comparison)
        if (type(result.outputs) is not list or len(result.outputs) != 1
                or type(result.outputs[0]) is not str):
            raise ValueError("source_comparison_refused")
        print(result.outputs[0], flush=True)
        return 0
    except (Exception, KeyboardInterrupt):
        try:
            print(json.dumps({"error_code": "source_comparison_refused"}),
                  file=sys.stderr, flush=True)
        except (OSError, UnicodeError, ValueError):
            _silence_broken_standard_stream(sys.stderr, 2)
        _silence_broken_standard_stream(sys.stdout, 1)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
