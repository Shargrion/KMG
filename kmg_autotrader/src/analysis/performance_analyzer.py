"""Performance metrics computation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Trade:
    pnl: float


def compute_metrics(trades: List[Trade]) -> dict[str, float]:
    """Return basic PnL statistics."""
    total_return = sum(t.pnl for t in trades)
    win_trades = [t for t in trades if t.pnl > 0]
    loss_trades = [t for t in trades if t.pnl <= 0]
    win_rate = len(win_trades) / len(trades) if trades else 0.0
    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "trades": len(trades),
    }
