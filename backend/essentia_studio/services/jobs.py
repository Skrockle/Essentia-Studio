from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any

from essentia_studio.domain.jobs import JobItem, JobRecord, JobStatus, JobType
from essentia_studio.errors import AppError
from essentia_studio.repositories.jobs import JobRepository

JobHandler = Callable[[str, str, Event], dict[str, Any]]
logger = logging.getLogger(__name__)


class JobCoordinator:
    def __init__(
        self,
        repository: JobRepository,
        handlers: dict[JobType, JobHandler],
        worker_counts: dict[JobType, int] | None = None,
    ) -> None:
        self._repository = repository
        self._handlers = handlers
        self._worker_counts = worker_counts or {}
        self._queue: Queue[str] = Queue()
        self._shutdown = Event()
        self._active_cancellations: dict[str, Event] = {}
        self._active_lock = Lock()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = Thread(target=self._run_forever, name="essentia-job-worker", daemon=True)
        self._thread.start()

    def register_handler(self, job_type: JobType, handler: JobHandler) -> None:
        if self._thread is not None:
            raise RuntimeError("Job handlers must be registered before the coordinator starts")
        self._handlers[job_type] = handler

    def stop(self) -> None:
        self._shutdown.set()
        with self._active_lock:
            for cancellation in self._active_cancellations.values():
                cancellation.set()
        if self._thread is not None:
            self._thread.join(timeout=10)

    def submit(
        self,
        job_type: JobType,
        items: Sequence[str],
        configuration: dict[str, Any],
        parent_job_id: str | None = None,
    ) -> JobRecord:
        job = self._repository.create(job_type, items, configuration, parent_job_id)
        self._queue.put(job.id)
        return job

    def cancel(self, job_id: str) -> JobRecord:
        self._repository.request_cancel(job_id)
        with self._active_lock:
            cancellation = self._active_cancellations.get(job_id)
            if cancellation is not None:
                cancellation.set()
        return self._repository.get(job_id)

    def resume(self, job_id: str) -> JobRecord:
        original = self._repository.get(job_id)
        unfinished_items = self._repository.item_values(job_id, unfinished_only=True)
        if not unfinished_items:
            raise AppError(
                "job_not_resumable",
                "Dieser Job enthält keine offenen oder fehlgeschlagenen Titel.",
                409,
            )
        return self.submit(
            original.type,
            unfinished_items,
            original.configuration,
            parent_job_id=original.id,
        )

    def run_next_for_test(self) -> None:
        self._run_job(self._queue.get_nowait())

    def _run_forever(self) -> None:
        while not self._shutdown.is_set():
            try:
                job_id = self._queue.get(timeout=0.2)
            except Empty:
                continue
            self._run_job(job_id)

    def _run_job(self, job_id: str) -> None:
        cancellation = Event()
        with self._active_lock:
            self._active_cancellations[job_id] = cancellation

        try:
            self._repository.start(job_id)
            job = self._repository.get(job_id)
            handler = self._handlers[job.type]
            self._process_items(
                job_id,
                self._repository.pending_items(job_id),
                handler,
                cancellation,
                self._worker_counts.get(job.type, 1),
            )
            self._finish_job(job_id, cancellation)
        except Exception:
            self._repository.finalize(job_id, JobStatus.FAILED)
            logger.exception("Job %s failed before item-level recovery", job_id)
        finally:
            with self._active_lock:
                self._active_cancellations.pop(job_id, None)

    def _process_items(
        self,
        job_id: str,
        items: list[JobItem],
        handler: JobHandler,
        cancellation: Event,
        worker_count: int,
    ) -> None:
        if worker_count <= 1:
            for item in items:
                if self._should_stop(job_id, cancellation):
                    break
                self._process_item(job_id, item.id, item.value, handler, cancellation)
            return

        item_iterator = iter(items)
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="analysis-item",
        ) as pool:
            pending: set[Future[None]] = set()
            self._submit_next_items(
                pool, pending, item_iterator, job_id, handler, cancellation, worker_count
            )
            while pending:
                completed, pending = wait(pending, return_when=FIRST_COMPLETED)
                if self._should_stop(job_id, cancellation):
                    continue
                self._submit_next_items(
                    pool, pending, item_iterator, job_id, handler, cancellation, len(completed)
                )

    def _submit_next_items(
        self,
        pool: ThreadPoolExecutor,
        pending: set[Future[None]],
        item_iterator,
        job_id: str,
        handler: JobHandler,
        cancellation: Event,
        limit: int,
    ) -> None:
        for _ in range(limit):
            if self._should_stop(job_id, cancellation):
                return
            try:
                item = next(item_iterator)
            except StopIteration:
                return
            pending.add(
                pool.submit(self._process_item, job_id, item.id, item.value, handler, cancellation)
            )

    def _should_stop(self, job_id: str, cancellation: Event) -> bool:
        if self._repository.is_cancel_requested(job_id):
            cancellation.set()
        return cancellation.is_set()

    def _process_item(
        self,
        job_id: str,
        item_id: int,
        value: str,
        handler: JobHandler,
        cancellation: Event,
    ) -> None:
        try:
            result = handler(job_id, value, cancellation)
            self._repository.complete_item(job_id, item_id, result)
        except Exception as error:
            self._repository.fail_item(job_id, item_id, str(error))

    def _finish_job(self, job_id: str, cancellation: Event) -> None:
        job = self._repository.get(job_id)
        if cancellation.is_set() or job.cancel_requested:
            status = JobStatus.CANCELLED
        elif job.failed_items:
            status = JobStatus.COMPLETED_WITH_ERRORS
        else:
            status = JobStatus.COMPLETED
        self._repository.finalize(job_id, status)
