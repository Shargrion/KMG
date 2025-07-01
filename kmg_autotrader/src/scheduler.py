"""Simple job scheduler for KMG Autotrader."""

from __future__ import annotations

import logging
import sched
import threading
import time
from typing import Callable


class Scheduler:
    """Manage periodic jobs using :mod:`sched`."""

    def __init__(self, gpt_trigger: object, ml_trainer: object, performance_analyzer: object) -> None:
        self._trigger = gpt_trigger
        self._trainer = ml_trainer
        self._analyzer = performance_analyzer
        self._sched = sched.scheduler(time.time, time.sleep)
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ------------------------------------------------------------------
    def _wrap(self, func: Callable[[], None], interval: int) -> Callable[[], None]:
        lock = threading.Lock()

        def job() -> None:
            if not lock.acquire(blocking=False):
                logging.info("Job %s skipped: already running", getattr(func, "__name__", "func"))
                self._sched.enter(interval, 1, job)
                return
            logging.info("Job %s started", getattr(func, "__name__", "func"))
            try:
                func()
            finally:
                lock.release()
                logging.info("Job %s finished", getattr(func, "__name__", "func"))
                self._sched.enter(interval, 1, job)

        return job

    def _setup_jobs(self) -> None:
        self._sched.enter(10, 1, self._wrap(self._trigger.check_new_signals, 10))
        self._sched.enter(3600, 1, self._wrap(self._trainer.update_model, 3600))
        self._sched.enter(86400, 1, self._wrap(self._analyzer.export_daily_report, 86400))

    # ------------------------------------------------------------------
    def start(self) -> None:
        """Configure and start background scheduler thread."""

        self._setup_jobs()
        logging.info("Scheduler started")
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._sched.run(blocking=False)
            time.sleep(1)

    def stop(self) -> None:
        """Stop scheduler and wait for thread termination."""

        logging.info("Scheduler stopping")
        self._stop.set()
        self._thread.join(timeout=5)
        logging.info("Scheduler stopped")


__all__ = ["Scheduler"]
