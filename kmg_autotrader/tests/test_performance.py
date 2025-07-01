"""Performance analyzer tests."""

from src.analysis.performance_analyzer import Trade, compute_metrics


def test_metrics():
    trades = [Trade(pnl=1), Trade(pnl=-1), Trade(pnl=2)]
    metrics = compute_metrics(trades)
    assert metrics["total_return"] == 2
    assert metrics["trades"] == 3
    assert metrics["win_rate"] == 2 / 3
