"""Explicit provider-account CLI, not a JARVIS public login/action endpoint."""

from __future__ import annotations

import importlib.util
import json
import re
import webbrowser

from apps.jarvis_console.bootstrap import ROOT
from apps.jarvis_console.registry import CommandExecutionResult
from apps.jarvis_console.review_input import _requires_redaction
from apps.jarvis_console.runtime import ConsoleCommandError, ConsoleExitCode, ConsoleRuntime


def run_chatgpt_account(args) -> CommandExecutionResult:
    # Opt-in is checked before importing OAuth modules, reading storage, binding
    # a socket, launching a browser or making any external request.
    if args.authorized is not True:
        raise ConsoleCommandError(
            "Provider account operations require --authorized and an explicit private directory.",
            error_code="siwc_not_authorized", exit_code=ConsoleExitCode.USAGE_ERROR,
        )
    try:
        if (type(args.timeout_seconds) is not int or not 1 <= args.timeout_seconds <= 600
                or args.action not in {"profiles", "connect", "catalog", "refresh"}
                or (args.profile_ref is not None
                    and (type(args.profile_ref) is not str
                         or re.fullmatch(r"profile-[0-9a-f]{64}", args.profile_ref) is None))):
            raise ValueError("siwc_input_invalid")
        from inference_service.credential_store import SiwcCredentialStore
        from inference_service.oauth_http import SiwcHttpsClient
        from inference_service.oauth_listener import SiwcLoopbackListener
        from inference_service.siwc_session import SiwcSession

        store = SiwcCredentialStore(args.credential_dir, authorized=True)
        if args.action == "profiles":
            # Existing store only; no network, directory init or browser.
            refs = store.profiles()
            payload = {"mode": "siwc_profiles", "profile_count": len(refs),
                       "profile_refs": list(refs), "network_used": False, "authority": "none"}
        elif args.action == "connect":
            if importlib.util.find_spec("jwt") is None:
                raise ValueError("siwc_identity_dependency_missing")
            host = store.initialize()
            client = SiwcHttpsClient(authorized=True)
            session = SiwcSession(host_id=host, client=client, store=store)
            returning = args.profile_ref is not None
            if returning:
                previous = store.load_profile(args.profile_ref)
                session.load(client_id=previous.client_id, subject=previous.subject)
            with SiwcLoopbackListener(
                authorized=True, timeout_seconds=args.timeout_seconds,
            ) as listener:
                attempt = session.begin(redirect_uri=listener.redirect_uri, authorized=True,
                                        returning=returning, timeout_seconds=args.timeout_seconds)
                # This fixed-origin URL intentionally stays out of terminal/JSON/logs;
                # it may contain an id_token_hint on reauthorization.
                if not webbrowser.open(attempt.authorization_url, new=1, autoraise=True):
                    raise ValueError("siwc_browser_unavailable")
                callback = listener.receive(attempt)
                identity = session.complete(attempt, callback, timeout_seconds=30)
            credentials = store.load(client_id=identity.client_id, subject=identity.subject)
            payload = {**session.metadata(), "profile_ref": store.profile_ref(credentials),
                       "browser_opened": True, "network_used": True,
                       "runtime_capability_promoted": False}
        else:
            if args.profile_ref is None:
                raise ValueError("siwc_account_missing")
            credentials = store.load_profile(args.profile_ref)
            client = SiwcHttpsClient(authorized=True)
            session = SiwcSession(host_id=store.host_id(), client=client, store=store)
            session.load(client_id=credentials.client_id, subject=credentials.subject)
            if args.action == "refresh":
                payload = session.refresh(authorized=True)
                payload["network_used"] = True
            elif args.action == "catalog":
                catalog = session.catalog(authorized=True)
                payload = {**catalog.metadata(), "network_used": True,
                           "models": [{"slug": item.slug, "display_name": item.display_name}
                                      for item in catalog.choices]}
            else:
                raise ValueError("siwc_action_invalid")
        redactor = ConsoleRuntime(output_format="json", sensitive_paths=(str(ROOT),))
        if _requires_redaction(payload, redactor):
            # Withhold display entries as a whole rather than mangling exact slugs.
            if "models" in payload:
                payload.pop("models")
                payload["models_withheld"] = True
            else:
                raise ValueError("siwc_display_refused")
        encoded = json.dumps(payload, ensure_ascii=True, allow_nan=False, sort_keys=True)
        if len(encoded.encode("ascii")) > 262_144 or redactor.redact(encoded)[1]:
            raise ValueError("siwc_display_refused")
        return CommandExecutionResult(outputs=[encoded])
    except Exception:
        raise ConsoleCommandError(
            "ChatGPT account operation refused; check the private store, consent and connection.",
            error_code="siwc_operation_refused", exit_code=ConsoleExitCode.USAGE_ERROR,
        ) from None
