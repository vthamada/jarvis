"""One explicit fixture step; no generic executor, subprocess or tool port."""

from .store import CORE_TASK, JobSnapshot, JobStoreError, SqliteJobStore, _ref


class FixtureJobWorker:
    def __init__(self, store: SqliteJobStore, worker_id: str):
        if not isinstance(store, SqliteJobStore):
            raise ValueError("invalid_fixture_store")
        _ref(worker_id)
        self.store = store
        self.worker_id = worker_id

    def run_once(
        self,
        job_id: str,
        *,
        actor_ref: str,
        session_ref: str,
        expected_version: int,
        lease_seconds: float = 30,
    ) -> JobSnapshot:
        before = self.store.get(job_id, actor_ref=actor_ref, session_ref=session_ref)
        if before.spec.task_ref == CORE_TASK:
            raise JobStoreError("fixture_worker_core_refused")
        claim = self.store.claim(
            job_id,
            worker_id=self.worker_id,
            actor_ref=actor_ref,
            session_ref=session_ref,
            expected_version=expected_version,
            lease_seconds=lease_seconds,
        )
        if claim is None:
            return self.store.get(job_id, actor_ref=actor_ref, session_ref=session_ref)
        snapshot = self.store.get(job_id, actor_ref=actor_ref, session_ref=session_ref)
        # No caller-supplied callable, output, prompt, source or action is executed.
        outcome = {
            "fixture:success": "succeeded",
            "fixture:failure": "failed",
            "fixture:needs_decision": "needs_decision",
        }[snapshot.spec.task_ref]
        return self.store.finish(claim, outcome)
