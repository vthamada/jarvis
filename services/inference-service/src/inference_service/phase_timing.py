"""Content-free diagnostic phases; observers never confer inference authority."""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic

_PHASES = frozenset({
    "connect_complete", "request_sent", "first_byte", "headers_validated",
    "body_complete", "peer_closed", "provider_parse_complete",
})


def emit_phase(observer: Callable[[dict[str, object]], None], phase: str, *,
               elapsed_seconds: float, clock: Callable[[], float]) -> None:
    """Emit one fixed metadata record; callers own pre/post callback fences.

    Elapsed time is cumulative from this transport/provider operation's start,
    not from object construction. ``live`` classifies the monotonic clock only;
    it says nothing about actual model execution or local weights. No request,
    response, endpoint, identity, token counts or exception strings are included.
    """
    if phase not in _PHASES:
        raise ValueError("invalid_local_inference_phase")
    event = {
        "event": "local_inference_phase", "phase": phase,
        "elapsed_ms": min(120_000, max(0, int(elapsed_seconds * 1000))),
        "timing_mode": "live" if clock is monotonic else "injected_clock",
    }
    try:
        observer(event)
    except Exception:
        # The surrounding pre/post checks still revoke late publication when
        # the observer changes configuration, cancellation or remaining time.
        pass
