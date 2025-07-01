"""Performance metrics computation.

This module exposes helper utilities to calculate trading performance metrics
based on records stored in PostgreSQL.  It can still operate on a list of
``Trade`` instances for unit tests, but production use relies on the
``TradeLog`` SQLAlchemy model.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from collections import deque
import logging
from typing import Iterable, List, Tuple

from sqlalchemy.orm import Session

from src.db import SessionLocal
from src.db.models import TradeLog, TradeStatus


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


# --- Database backed utilities -------------------------------------------------

_CACHE: deque[TradeLog] = deque(maxlen=100)


def _refresh_cache(session: Session) -> None:
    """Load the latest trades from the database into the local cache."""
    logging.debug("Refreshing trade cache")
    trades = (
        session.query(TradeLog)
        .order_by(TradeLog.timestamp.desc())
        .limit(_CACHE.maxlen)
        .all()
    )
    _CACHE.clear()
    _CACHE.extendleft(reversed(trades))


def get_recent_trades(session: Session | None = None) -> list[TradeLog]:
    """Return cached recent trades, reloading if the cache is empty."""
    session = session or SessionLocal()
    if not _CACHE:
        _refresh_cache(session)
    return list(_CACHE)


def equity_curve(trades: Iterable[TradeLog]) -> List[Tuple[datetime, float]]:
    """Calculate cumulative equity over time."""
    equity = 0.0
    curve: list[tuple[datetime, float]] = []
    for trade in sorted(trades, key=lambda t: t.timestamp):
        equity += trade.pnl or 0.0
        curve.append((trade.timestamp, equity))
    return curve


def winrate(trades: Iterable[TradeLog]) -> float:
    """Return the ratio of profitable trades to total completed trades."""
    wins = 0
    total = 0
    for trade in trades:
        if trade.status == TradeStatus.REJECTED:
            continue
        total += 1
        if trade.status == TradeStatus.WIN:
            wins += 1
    return wins / total if total else 0.0


def max_drawdown(curve: Iterable[Tuple[datetime, float]]) -> float:
    """Compute maximum drawdown from an equity curve."""
    peak = float("-inf")
    max_dd = 0.0
    for _, equity in curve:
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


def compute_db_metrics(session: Session | None = None) -> dict[str, float | list[tuple[str, float]]]:
    """Compute metrics using ``TradeLog`` records from the database."""
    session = session or SessionLocal()
    trades = get_recent_trades(session)
    curve = equity_curve(trades)
    wr = winrate(trades)
    dd = max_drawdown(curve)
    logging.info(
        "Computed DB metrics: winrate %.2f, max DD %.2f over %d trades",
        wr,
        dd,
        len(trades),
    )
    return {
        "equity_curve": [(ts.isoformat(), val) for ts, val in curve],
        "win_rate": wr,
        "max_drawdown": dd,
        "trades": len(trades),
    }
