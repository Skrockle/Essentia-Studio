from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
from threading import Event, Lock, Thread
from typing import Any

from essentia_studio.domain.jobs import JobItem, JobRecord, JobStatus, JobType
from essentia_studio.errors import AppError
from essentia_studio.repositories.jobs import JobRepository

JobHandler = Callable[[str, str, Event], dict[str, Any]]
TerminalListener = Callable[[JobRecord], None]
logger = logging.getLogger(__name__)


class JobCoordinator:
    def __init__(self, repository: JobRepository, handlers: dict[JobType, JobHandler]) -> None:
        self._repository = repository
        self._handlers = handlers
        self._queue: Queue[str] = Queue()
        self._shutdown = Event()
        self._active_cancellations: dict[str, Event] = {}
        self._active_lock = Lock()
        self._thread: Thread | None = None
        self._terminal_listeners: list[TerminalListener] = []

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = Thread(target=self._run_forever, name="essentia-job-worker", daemon=True)
        self._thread.start()

    def register_handler(self, job_type: JobType, handler: JobHandler) -> None:
        if self._thread is not None:
            raise RuntimeError("Job handlers must be registered before the coordinator starts")
        self._handlers[job_type] = handler

    def add_terminal_listener(self, listener: TerminalListener) -> None:
        self._terminal_listeners.append(listener)

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
            pending_items = self._repository.pending_items(job_id)
            worker_count = self._worker_count(job)
            if worker_count > 1:
                self._process_parallel(
                    job_id,
                    pending_items,
                    handler,
                    cancellation,
                    worker_count,
                )
            else:
                self._process_serial(job_id, pending_items, handler, cancellation)
            self._finish_job(job_id, cancellation)
        except Exception:
            finalized = self._repository.finalize(job_id, JobStatus.FAILED)
            self._notify_terminal(finalized)
            logger.exception("Job %s failed before item-level recovery", job_id)
        finally:
            with self._active_lock:
                self._active_cancellations.pop(job_id, None)

    def _process_serial(
        self,
        job_id: str,
        items: Sequence[JobItem],
        handler: JobHandler,
        cancellation: Event,
    ) -> None:
        for item in items:
            if self._repository.is_cancel_requested(job_id):
                cancellation.set()
            if cancellation.is_set():
                break
            self._process_item(job_id, item.id, item.value, handler, cancellation)

    def _process_parallel(
        self,
        job_id: str,
        items: Sequence[JobItem],
        handler: JobHandler,
        cancellation: Event,
        worker_count: int,
    ) -> None:
        def process(item: JobItem) -> None:
            if cancellation.is_set():
                return
            if self._repository.is_cancel_requested(job_id):
                cancellation.set()
                return
            self._process_item(job_id, item.id, item.value, handler, cancellation)

        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="essentia-analysis",
        ) as executor:
            list(executor.map(process, items))

    @staticmethod
    def _worker_count(job: JobRecord) -> int:
        if job.type != JobType.ANALYSIS:
            return 1
        configured = job.configuration.get("worker_count", 1)
        if isinstance(configured, bool) or not isinstance(configured, int):
            return 1
        return max(1, min(configured, 64))

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
        except AppError as error:
            logger.exception(
                "Job item failed: job_id=%s item_id=%s value=%s error_code=%s",
                job_id,
                item_id,
                value,
                error.code,
            )
            self._repository.fail_item(
                job_id,
                item_id,
                error.message,
                error_code=error.code,
            )
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
        finalized = self._repository.finalize(job_id, status)
        self._notify_terminal(finalized)

    def _notify_terminal(self, job: JobRecord) -> None:
        for listener in self._terminal_listeners:
            try:
                listener(job)
            except Exception:
                logger.exception("Terminal listener failed for job %s", job.id)
