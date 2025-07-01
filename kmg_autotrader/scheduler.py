"""Async task scheduler for KMG-Autotrader."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger


def _wrap(func: Callable[[], Any]) -> Callable[[], Awaitable[None]]:
    """Wrap job function to support sync or async call with logging."""

    async def runner() -> None:
        logging.info("Running task %s", func.__name__)
        result = func()
        if asyncio.iscoroutine(result):
            await result

    return runner


def start_scheduler(
    gpt_trigger: Any, ml_trainer: Any, performance_analyzer: Any
) -> AsyncIOScheduler:
    """Create and start the global scheduler with all jobs."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        _wrap(gpt_trigger.check_new_signals),
        IntervalTrigger(seconds=10),
        max_instances=1,
        coalesce=True,
        id="check_signals",
    )
    scheduler.add_job(
        _wrap(ml_trainer.update_model),
        IntervalTrigger(hours=1),
        max_instances=1,
        coalesce=True,
        id="update_model",
    )
    scheduler.add_job(
        _wrap(performance_analyzer.export_daily_report),
        IntervalTrigger(hours=24),
        max_instances=1,
        coalesce=True,
        id="daily_report",
    )
    scheduler.start()
    return scheduler
