"""Risk management for trading operations."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from src.webui.alerts.telegram_bot import send_alert


@dataclass
class RiskParameters:
    max_position_percent: float
    max_drawdown: float


class RiskManager:
    """Validate trading signals against risk parameters."""

    def __init__(self, params: RiskParameters) -> None:
        """Initialize with risk parameters."""
        self._params = params
        self._current_drawdown = 0.0

    def validate(self, size: float) -> bool:
        """Check if trade size is within limits."""
        if size > self._params.max_position_percent:
            logging.warning("Trade size %.2f exceeds limit", size)
            send_alert("Signal rejected: size limit")
            return False
        if self._current_drawdown > self._params.max_drawdown:
            logging.error("Drawdown limit reached")
            send_alert("Risk exceeded: drawdown limit")
            return False
        logging.debug("Risk validation passed for size %.2f", size)
        return True
