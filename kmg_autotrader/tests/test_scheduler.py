import threading
import time
from unittest import mock

from src.scheduler import Scheduler


def test_job_intervals(monkeypatch):
    intervals = []

    def fake_enter(delay, priority, action, argument=(), kwargs=None):
        intervals.append(delay)
        return None

    gt = mock.Mock()
    trainer = mock.Mock()
    analyzer = mock.Mock()

    scheduler = Scheduler(gt, trainer, analyzer)
    monkeypatch.setattr(scheduler._sched, "enter", fake_enter)
    scheduler._setup_jobs()

    assert 10 in intervals
    assert 3600 in intervals
    assert 86400 in intervals


def test_no_duplicate_runs():
    gt = mock.Mock()
    scheduler = Scheduler(gt, mock.Mock(), mock.Mock())
    wrapped = scheduler._wrap(gt.check_new_signals, 1)

    event = threading.Event()

    def side_effect():
        event.wait(0.2)

    gt.check_new_signals.side_effect = side_effect

    t = threading.Thread(target=wrapped)
    t.start()
    time.sleep(0.05)
    wrapped()
    event.set()
    t.join()

    assert gt.check_new_signals.call_count == 1
