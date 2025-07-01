"""Manage GPT invocation frequency and scheduling."""

import asyncio
import logging
import sqlite3
from typing import Iterable, TYPE_CHECKING, Any

from src.collector.binance_data_collector import Candle
from src.evaluator.rule_evaluator import Signal
from src.risk.risk_manager import RiskManager
from src.webui.alerts.telegram_bot import send_alert
from .gpt_controller import GPTController, DB_PATH

if TYPE_CHECKING:  # pragma: no cover - only for typing
    from src.executor.executor import Executor, Order
else:  # Fallback to avoid importing binance during tests
    from dataclasses import dataclass

    class Order:  # pragma: no cover - simplified placeholder
        def __init__(self, asset: str, side: str, quantity: float) -> None:
            self.asset = asset
            self.side = side
            self.quantity = quantity

    class Executor:  # pragma: no cover - simplified placeholder
        def place_order(self, order: Order) -> bool:  # noqa: D401 - placeholder
            """Place order on exchange."""
            raise NotImplementedError


class GPTTrigger:
    """Rate-limited trigger for GPT requests."""

    def __init__(
        self,
        controller: GPTController,
        risk_manager: RiskManager,
        executor: Executor,
        max_per_hour: int,
    ) -> None:
        """Create a new trigger with dependencies and call limit."""

        self._controller = controller
        self._risk_manager = risk_manager
        self._executor = executor
        self._max_per_hour = max_per_hour
        self._count = 0
        self._lock = asyncio.Lock()

    def _log_refusal(self, reason: str) -> None:
        """Record a refusal reason to the GPT log database."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "INSERT INTO gpt_logs(prompt, response, success, reason) VALUES (?, ?, ?, ?)",
                    ("", "", 0, reason),
                )
        except sqlite3.DatabaseError as exc:  # pragma: no cover - log failure
            logging.error("Failed to log GPT refusal: %s", exc)

    async def allow(self) -> bool:
        """Return ``True`` if a GPT call is permitted."""
        async with self._lock:
            if self._count >= self._max_per_hour:
                logging.warning("GPT call blocked: limit reached")
                send_alert("GPT limit reached: signal skipped")
                self._log_refusal("limit reached")
                return False
            self._count += 1
            logging.debug("GPT call allowed (%d/%d)", self._count, self._max_per_hour)
            return True

    async def reset(self) -> None:
        """Reset counter every hour."""
        while True:
            await asyncio.sleep(3600)
            async with self._lock:
                self._count = 0

    async def process(
        self,
        signal: Signal,
        candles: Iterable[Candle],
        position: float,
    ) -> bool:
        """Validate the signal and, if allowed, execute GPT-driven order."""

        if signal.direction not in {"BUY", "SELL"}:
            logging.warning("Unsupported signal direction: %s", signal.direction)
            send_alert(f"Signal rejected: unsupported direction {signal.direction}")
            self._log_refusal("unsupported direction")
            return False

        if self._risk_manager._params.risk_mode == "conservative":
            logging.info("Conservative mode active - skipping GPT")
            self._log_refusal("conservative mode")
            return False

        if signal.score < self._risk_manager._params.min_gpt_trigger_confidence:
            reason = (
                f"Rule score {signal.score:.2f} below threshold "
                f"{self._risk_manager._params.min_gpt_trigger_confidence:.2f}"
            )
            logging.info(reason)
            self._log_refusal(reason)
            return False

        if not await self.allow():
            return False

        response = self._controller.request_decision(
            list(candles)[-10:], position, self._risk_manager._params
        )
        if response is None:
            send_alert("Signal rejected: GPT response invalid")
            self._log_refusal("invalid GPT response")
            return False

        if response.confidence < self._risk_manager._params.min_confidence:
            logging.warning(
                "GPT confidence %.2f below minimum %.2f",
                response.confidence,
                self._risk_manager._params.min_confidence,
            )
            send_alert("Signal rejected: low confidence")
            self._log_refusal("low GPT confidence")
            return False

        adj_size = self._risk_manager.scale_size(response.size)

        if not self._risk_manager.validate(adj_size):
            logging.warning("GPT proposal rejected by risk manager")
            send_alert("Signal rejected by risk manager")
            self._log_refusal("risk manager rejection")
            return False

        order = Order(asset=signal.asset, side=response.direction, quantity=adj_size)
        success = self._executor.place_order(order)
        if success:
            send_alert(
                f"Trade executed: {order.side} {order.quantity:.4f} {order.asset}"
            )
        return success

    def check_new_signals(self) -> None:
        """Placeholder for polling new trading signals."""
        logging.info("Checking for new signals")
