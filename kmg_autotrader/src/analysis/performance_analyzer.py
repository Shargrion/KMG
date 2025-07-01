"""Performance metrics computation."""

from __future__ import annotations

from dataclasses import dataclass
import logging


@dataclass
class Trade:
    """Record of a completed trade with profit or loss."""

    pnl: float


def compute_metrics(trades: list[Trade]) -> dict[str, float]:
    """Return basic PnL statistics and log the results."""
    total_return = sum(t.pnl for t in trades)
    win_trades = [t for t in trades if t.pnl > 0]
    loss_trades = [t for t in trades if t.pnl <= 0]
    win_rate = len(win_trades) / len(trades) if trades else 0.0
    metrics = {
        "total_return": total_return,
        "win_rate": win_rate,
        "trades": len(trades),
    }
    logging.info(
        "Computed metrics: return %.2f over %d trades (win rate %.2f)",
        total_return,
        len(trades),
        win_rate,
    )
    return metrics


def export_daily_report() -> None:
    """Export daily performance metrics to persistent storage."""
    logging.info("Exporting daily performance report")
