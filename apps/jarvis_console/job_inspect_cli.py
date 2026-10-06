"""Read-only console projection; does not bootstrap Core or a writable store."""

from pathlib import Path

from job_service.readonly import build_job_inspection as _build


def build_job_inspection(
    database_path: Path,
    *,
    actor_ref: str,
    session_ref: str,
    job_ids: tuple[str, ...],
    include_refs: bool = False,
) -> dict:
    """Delegate to the bounded ledger reader without adding authority."""
    return _build(
        database_path,
        actor_ref=actor_ref,
        session_ref=session_ref,
        job_ids=job_ids,
        include_refs=include_refs,
    )
