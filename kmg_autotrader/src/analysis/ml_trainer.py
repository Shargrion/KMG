"""Machine learning model trainer.

This module loads trades from the local SQLite database, extracts a set of very
basic features and trains a binary classifier estimating whether a signal will
be profitable.  The resulting model is saved to ``project_metadata/MLModels`` so
that other modules (e.g. :mod:`risk_manager`) can make use of it when GPT
approval is not available.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

import pickle

# --------------------------------------------------
# Simple classifier used instead of scikit-learn to
# avoid heavy dependencies in the test environment.
# It classifies based on distance to the mean feature
# vector of winning and losing trades.

class SimpleModel:
    """Extremely small classifier using a nearest-mean rule."""

    win_mean: list[float]
    lose_mean: list[float]

    def fit(self, X: list[list[float]], y: list[int]) -> None:
        wins = [x for x, lbl in zip(X, y) if lbl == 1]
        losses = [x for x, lbl in zip(X, y) if lbl == 0]
        n_features = len(X[0]) if X else 0
        self.win_mean = [sum(vals) / len(wins) for vals in zip(*wins)] if wins else [0.0] * n_features
        self.lose_mean = [sum(vals) / len(losses) for vals in zip(*losses)] if losses else [0.0] * n_features

    def predict(self, X: list[list[float]]) -> list[int]:
        preds = []
        for x in X:
            dist_win = sum((xi - wi) ** 2 for xi, wi in zip(x, self.win_mean))
            dist_loss = sum((xi - li) ** 2 for xi, li in zip(x, self.lose_mean))
            preds.append(1 if dist_win <= dist_loss else 0)
        return preds

# Paths ---------------------------------------------------------------------

# Database with trade history. ``gpt_log_archive.db`` is used as a lightweight
# store for various logs in this simplified code base, so we reuse it for
# ``trade_log`` as well.
DB_PATH = (
    Path(__file__).resolve().parents[2] / "project_metadata" / "gpt_log_archive.db"
)

# Where the trained model will be persisted.
MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "project_metadata"
    / "MLModels"
    / "model_v1.pkl"
)


# Data containers -----------------------------------------------------------

@dataclass
class TradeLog:
    """Single trade record loaded from the database."""

    entry_price: float
    exit_price: float
    entry_time: int
    exit_time: int
    volume: float


def _load_trades() -> list[TradeLog]:
    """Load all trades from the SQLite ``trade_log`` table."""

    if not DB_PATH.exists():
        logging.warning("Trade DB %s does not exist", DB_PATH)
        return []

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT entry_price, exit_price, entry_time, exit_time, volume FROM trade_log"
        ).fetchall()
    except sqlite3.DatabaseError as exc:
        logging.error("Failed loading trades: %s", exc)
        return []
    finally:
        conn.close()

    trades = [TradeLog(*r) for r in rows]
    logging.info("Loaded %d trades from DB", len(trades))
    return trades


def _ema(values: Iterable[float], period: int = 14) -> list[float]:
    """Return Exponential Moving Average for the provided sequence."""

    values = list(values)
    if not values:
        return []

    k = 2 / (period + 1)
    ema: list[float] = [values[0]]
    for val in values[1:]:
        ema.append(val * k + ema[-1] * (1 - k))
    return ema


def _rsi(values: Iterable[float], period: int = 14) -> list[float]:
    """Calculate a very simple Relative Strength Index."""

    values = list(values)
    if len(values) < 2:
        return [50.0 for _ in values]  # Neutral RSI if insufficient data

    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]

    def calc_at(idx: int) -> float:
        start = max(0, idx - period + 1)
        gains = [max(d, 0.0) for d in deltas[start:idx + 1]]
        losses = [-min(d, 0.0) for d in deltas[start:idx + 1]]
        avg_gain = sum(gains) / period if gains else 0.0
        avg_loss = sum(losses) / period if losses else 0.0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - 100 / (1 + rs)

    rsi = [50.0]
    for i in range(1, len(values)):
        rsi.append(calc_at(i - 1))
    return rsi


def _build_features(trades: list[TradeLog]) -> Tuple[list[list[float]], list[int]]:
    """Transform raw trades into ML-ready features and labels."""

    if not trades:
        return [], []

    exit_prices = [t.exit_price for t in trades]
    ema_series = _ema(exit_prices)
    rsi_series = _rsi(exit_prices)

    features: list[list[float]] = []
    labels: list[int] = []

    for idx, trade in enumerate(trades):
        duration = trade.exit_time - trade.entry_time
        pnl = trade.exit_price - trade.entry_price
        speed = pnl / duration if duration else pnl

        feat = [
            trade.entry_price,
            trade.exit_price,
            speed,
            rsi_series[idx],
            ema_series[idx],
            trade.volume,
        ]
        features.append(feat)
        labels.append(1 if pnl > 0 else 0)

    return features, labels


def train() -> None:
    """Load trades, train a model and persist it to :data:`MODEL_PATH`."""

    trades = _load_trades()
    if not trades:
        logging.warning("No trades available for training")
        return

    X, y = _build_features(trades)

    clf = SimpleModel()
    clf.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("wb") as f:
        pickle.dump(clf, f)
    logging.info("Model trained and saved to %s", MODEL_PATH)


__all__ = ["train", "_load_trades", "_build_features", "TradeLog", "MODEL_PATH", "DB_PATH"]



def update_model() -> None:
    """Public entry for scheduler to retrain the model."""
    logging.info("Updating ML model")
    train()

__all__.append("update_model")

