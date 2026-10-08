"""Explicit fixed-server MCP read of the authored repository inventory, not Core."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "invalid_readiness_mcp_options\n")


async def _collect(binding, front_id, timeout_seconds):
    from apps.jarvis_mcp.readiness_client import FixedReadinessMcpClient

    client = FixedReadinessMcpClient(binding, authorized=True, timeout_seconds=timeout_seconds)
    try:
        await client.start()
        observation = await client.call(binding, "read_product_readiness", {"front_id": front_id})
        return observation.snapshot(), observation.metadata()
    finally:
        await client.close()


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--principal-ref", required=True)
    parser.add_argument("--session-ref", required=True)
    parser.add_argument(
        "--front-id",
        default="all",
        choices=(
            "all",
            *(f"F{i:02d}" for i in range(1, 14)),
            *(f"T{i:02d}" for i in range(1, 4)),
        ),
    )
    parser.add_argument("--timeout-seconds", type=float, default=3.0)
    parser.add_argument("--format", choices=("text", "json"), default="text")
    options = parser.parse_args(argv)
    if not options.authorized:
        print("readiness_mcp_authorization_required", file=sys.stderr)
        return 2
    try:
        from apps.jarvis_mcp.readiness_contracts import ReadinessBinding

        binding = ReadinessBinding(options.principal_ref, options.session_ref)
        snapshot, metadata = asyncio.run(
            _collect(binding, options.front_id, options.timeout_seconds)
        )
        if options.format == "json":
            rendered = json.dumps(
                {"metadata": metadata, "snapshot": snapshot}, ensure_ascii=False, allow_nan=False
            )
        else:
            from tools.product_readiness_report import render_text

            rendered = (
                "Local MCP: authored repository snapshot; no Core authority.\n"
                f"Selection: {options.front_id}. No runtime verification or human authentication.\n"
                + render_text(snapshot)
            )
        rendered.encode("utf-8", "strict")
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")
        print(rendered)
    except (Exception, KeyboardInterrupt):
        print("readiness_mcp_failed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
