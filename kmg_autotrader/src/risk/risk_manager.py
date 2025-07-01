"""Risk management for trading operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass


@dataclass
class RiskParameters:
    max_position_percent: float
    max_drawdown: float
    max_daily_loss: float


class RiskManager:
    """Validate trading signals against risk parameters."""

    def __init__(self, params: RiskParameters) -> None:
        self._params = params
        self._current_drawdown = 0.0
        self._daily_loss = 0.0
        self._equity = 0.0
        self._equity_peak = 0.0

    def update_pnl(self, pnl: float) -> None:
        """Update equity, drawdown, and daily loss from realized PnL."""
        self._equity += pnl
        if self._equity > self._equity_peak:
            self._equity_peak = self._equity
        self._current_drawdown = self._equity_peak - self._equity
        if pnl < 0:
            self._daily_loss += -pnl

    def reset_daily_loss(self) -> None:
        """Reset the accumulated daily loss."""
        self._daily_loss = 0.0

    def validate(self, size: float, exposure: float) -> bool:
        """Check if trade parameters are within risk limits."""
        if size > self._params.max_position_percent:
            logging.warning("Trade size %.2f exceeds limit", size)
            return False
        if exposure + size > self._params.max_position_percent:
            logging.warning("Exposure %.2f exceeds limit", exposure + size)
            return False
        if self._current_drawdown > self._params.max_drawdown:
            logging.error("Drawdown limit reached")
            return False
        if self._daily_loss > self._params.max_daily_loss:
            logging.error("Daily loss limit reached")
            return False
        return True
