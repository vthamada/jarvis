"""Explicit opt-in local analysis server with a fresh, retained owned runtime."""

from __future__ import annotations

import argparse
import json
import stat
import sys
from pathlib import Path
from threading import Lock
from uuid import uuid4

from apps.jarvis_console.bootstrap import ROOT


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "invalid_local_web_options\n")


def _diagnostic_printer():
    """Bounded host-only projection; never a Web response or authority grant."""
    from inference_service.diagnostics import emit_diagnostic

    count = 0
    lock = Lock()

    def write(record):
        nonlocal count
        with lock:
            if count >= 256:
                return
            count += 1
            print(json.dumps(record, ensure_ascii=True, allow_nan=False),
                  file=sys.stderr, flush=True)

    def receive(record):
        if type(record) is dict:
            emit_diagnostic(write, phase=record.get("phase"), status=record.get("status"),
                            code=record.get("code"), http_status=record.get("http_status"))

    return receive


def _directory(path: Path) -> None:
    """Do not follow an existing runtime junction/symlink into another store."""
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400):
            raise ValueError("local_web_runtime_refused")
    else:
        path.mkdir()


def create_owned_runtime(root: Path = ROOT) -> Path:
    """Only create a new child; never open, clean or reuse an existing runtime."""
    if not isinstance(root, Path) or not root.is_absolute() or not root.is_dir():
        raise ValueError("local_web_runtime_refused")
    _directory(root)
    runtime_parent = root / ".jarvis_runtime"
    _directory(runtime_parent)
    runtime_base = runtime_parent / "web-live"
    _directory(runtime_base)
    if not runtime_base.resolve().is_relative_to(root.resolve()):
        raise ValueError("local_web_runtime_refused")
    runtime = runtime_base / uuid4().hex
    runtime.mkdir(exist_ok=False)
    _directory(runtime)
    return runtime


def main(argv=None) -> int:
    parser = _Parser(description="Opt-in loopback Core analysis; models off by default, "
                                "no operational effects")
    parser.add_argument("--authorized", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--enable-generative", action="store_true")
    parser.add_argument("--inference-diagnostics", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--credential-dir", type=Path)
    parser.add_argument("--profile-ref")
    parser.add_argument("--generative-timeout-seconds", type=float)
    args = parser.parse_args(argv)
    if not args.authorized:
        print("local_web_authorization_required", file=sys.stderr)
        return 2
    if not 0 <= args.port <= 65535:
        print("invalid_local_web_options", file=sys.stderr)
        return 2
    profile = None
    try:
        configured = (args.model, args.credential_dir, args.profile_ref,
                      args.generative_timeout_seconds)
        if not args.enable_generative and any(value is not None for value in configured):
            raise ValueError("invalid_local_web_options")
        if args.inference_diagnostics and not args.enable_generative:
            raise ValueError("invalid_local_web_options")
        if args.enable_generative:
            from apps.jarvis_api.generative_profile import GenerativeProfile
            from apps.jarvis_console.bootstrap import ensure_src_paths

            ensure_src_paths()
            diagnostic_options = ({"diagnostic_sink": _diagnostic_printer()}
                                  if args.inference_diagnostics else {})
            profile = GenerativeProfile(
                authorized=True, model=args.model, credential_dir=args.credential_dir,
                profile_ref=args.profile_ref,
                timeout_seconds=(20.0 if args.generative_timeout_seconds is None
                                 else args.generative_timeout_seconds),
                **diagnostic_options,
            )
    except Exception:
        print("invalid_local_web_options", file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    server = service = None
    try:
        from apps.jarvis_api.analysis_service import AnalysisService
        from apps.jarvis_api.local_server import create_server

        runtime = create_owned_runtime()
        service = AnalysisService(runtime) if profile is None else AnalysisService(
            runtime, generative_profile=profile,
        )
        server = create_server(service, args.port)
        print(f"JARVIS LOCAL CORE: http://127.0.0.1:{server.server_port}/", flush=True)
        print(f"Pairing code (one use, 120s): {server.auth.pairing_secret}", flush=True)
        print(f"Retained runtime: .jarvis_runtime/web-live/{runtime.name}", flush=True)
        print("Local session only; no human identity, tools or operational effects.", flush=True)
        print("Generative complement: explicit per-ticket consent required."
              if profile is not None else "Generative complement: disabled.", flush=True)
        print("Ctrl+C stops the server; it does not undo canonical memory.", flush=True)
        server.serve_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        print("local_web_startup_or_runtime_refused", file=sys.stderr)
        return 2
    finally:
        if server is not None:
            server.auth.close()
        if service is not None:
            service.close()
        if server is not None:
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
