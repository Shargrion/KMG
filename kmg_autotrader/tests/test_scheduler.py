"""Tests for task scheduler."""

from types import SimpleNamespace

import scheduler


def test_scheduler_jobs(monkeypatch):
    added = []

    class DummyScheduler:
        def add_job(self, func, trigger, **kwargs):
            added.append((trigger, kwargs))
        def start(self):
            pass

    monkeypatch.setattr(scheduler, "AsyncIOScheduler", lambda: DummyScheduler())

    gpt = SimpleNamespace(check_new_signals=lambda: None)
    trainer = SimpleNamespace(update_model=lambda: None)
    perf = SimpleNamespace(export_daily_report=lambda: None)

    scheduler.start_scheduler(gpt, trainer, perf)

    assert len(added) == 3
    intervals = sorted(int(t.interval.total_seconds()) for t, _ in added)
    assert intervals == [10, 3600, 86400]
    assert all(kwargs["max_instances"] == 1 for _, kwargs in added)
