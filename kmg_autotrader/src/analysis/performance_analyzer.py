"""Performance metrics computation."""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Iterable

try:
    from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.orm import declarative_base, sessionmaker
    _HAS_SQLALCHEMY = True
except Exception:  # pragma: no cover - optional dependency may be missing
    _HAS_SQLALCHEMY = False

    class _Dummy:  # pragma: no cover - basic stub to satisfy type checkers
        def __getattr__(self, name: str) -> None:
            raise RuntimeError("SQLAlchemy is required for DB operations")

    Column = DateTime = Float = Integer = String = _Dummy()  # type: ignore
    SQLAlchemyError = Exception  # type: ignore

    def create_engine(*args: Any, **kwargs: Any):  # type: ignore
        raise RuntimeError("SQLAlchemy not installed")

    def declarative_base() -> Any:  # type: ignore
        class Base:  # pragma: no cover - placeholder
            pass

        return Base

    def sessionmaker(*args: Any, **kwargs: Any):  # type: ignore
        def _session():
            raise RuntimeError("SQLAlchemy not installed")

        return _session

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
_POSTGRES_URL = os.getenv(
    "POSTGRES_URL", "postgresql://kmg_user:password@localhost/kmg_autotrader"
)
_ENGINE = create_engine(_POSTGRES_URL, future=True) if _HAS_SQLALCHEMY else None
SessionLocal = sessionmaker(bind=_ENGINE) if _HAS_SQLALCHEMY else lambda: None
Base = declarative_base() if _HAS_SQLALCHEMY else object


class TradeLog(Base):  # type: ignore[misc]
    """SQLAlchemy ORM model representing executed or rejected trades."""

    __tablename__ = "trade_log"

    if _HAS_SQLALCHEMY:
        id = Column(Integer, primary_key=True, autoincrement=True)
        timestamp = Column(DateTime, index=True, nullable=False)
        symbol = Column(String(20), nullable=False)
        side = Column(String(4), nullable=False)
        entry_price = Column(Float, nullable=False)
        exit_price = Column(Float, nullable=False)
        pnl = Column(Float, nullable=False)
        status = Column(String(10), nullable=False)


if _HAS_SQLALCHEMY:
    try:
        Base.metadata.create_all(_ENGINE)
    except SQLAlchemyError as exc:  # pragma: no cover - db might be missing
        logging.error("Failed creating tables: %s", exc)


# ---------------------------------------------------------------------------
# Trade cache handling
# ---------------------------------------------------------------------------
_CACHE_TIMEOUT = 60.0  # seconds
_trade_cache: deque[TradeLog] = deque(maxlen=100)
_cache_ts = 0.0


def _refresh_cache(limit: int = 100) -> None:
    """Reload latest trades from the database."""
    global _cache_ts
    if not _HAS_SQLALCHEMY:
        logging.warning("SQLAlchemy not available; cache not refreshed")
        return
    try:
        with SessionLocal() as session:
            records = (
                session.query(TradeLog)
                .order_by(TradeLog.timestamp.desc())
                .limit(limit)
                .all()
            )
        records.reverse()
        _trade_cache.clear()
        _trade_cache.extend(records)
        _cache_ts = time.time()
        logging.debug("Loaded %d trades into cache", len(records))
    except SQLAlchemyError as exc:
        logging.error("Failed to load trades: %s", exc)


def get_recent_trades(limit: int = 100) -> list[TradeLog]:
    """Return cached trades, refreshing if necessary."""
    if time.time() - _cache_ts > _CACHE_TIMEOUT or len(_trade_cache) < limit:
        _refresh_cache(limit)
    return list(_trade_cache)[:limit]


@dataclass
class Trade:
    """Simple trade dataclass used in unit tests."""

    pnl: float


# ---------------------------------------------------------------------------
# Metrics calculations for DB trades
# ---------------------------------------------------------------------------

def pnl_equity(trades: Iterable[TradeLog]) -> list[float]:
    """Compute cumulative PnL for an iterable of trades."""
    equity: list[float] = []
    cumulative = 0.0
    for trade in trades:
        cumulative += float(trade.pnl)
        equity.append(cumulative)
    return equity


def winrate(trades: Iterable[TradeLog]) -> float:
    """Return win ratio for closed trades."""
    trade_list = [t for t in trades if t.status in ("WIN", "LOSS")]
    if not trade_list:
        return 0.0
    wins = sum(1 for t in trade_list if t.status == "WIN")
    return wins / len(trade_list)


def max_drawdown(equity: Iterable[float]) -> float:
    """Calculate the maximum drawdown of an equity curve."""
    peak = float("-inf")
    max_dd = 0.0
    for value in equity:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


# ---------------------------------------------------------------------------
# Legacy metrics for unit tests
# ---------------------------------------------------------------------------

def compute_metrics(trades: list[Trade]) -> dict[str, float]:
    """Return basic PnL statistics for a list of Trade dataclasses."""
    total_return = sum(t.pnl for t in trades)
    win_trades = [t for t in trades if t.pnl > 0]
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


def compute_db_metrics(limit: int = 100) -> dict[str, float]:
    """Compute metrics using trades stored in the database."""
    if not _HAS_SQLALCHEMY:
        logging.error("SQLAlchemy not installed; cannot compute DB metrics")
        return {
            "equity_curve": [],
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "trades": 0,
            "total_return": 0.0,
        }

    trades = get_recent_trades(limit)
    equity = pnl_equity(trades)
    metrics = {
        "equity_curve": equity,
        "win_rate": winrate(trades),
        "max_drawdown": max_drawdown(equity),
        "trades": len(trades),
        "total_return": equity[-1] if equity else 0.0,
    }
    logging.info(
        "DB metrics computed: return %.2f over %d trades (win rate %.2f, DD %.2f)",
        metrics["total_return"],
        metrics["trades"],
        metrics["win_rate"],
        metrics["max_drawdown"],
    )
    return metrics
