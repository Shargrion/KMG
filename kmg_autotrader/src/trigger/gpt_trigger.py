"""Manage GPT invocation frequency and scheduling."""

import asyncio
import logging
from typing import Iterable, TYPE_CHECKING, Any

from src.collector.binance_data_collector import Candle
from src.evaluator.rule_evaluator import Signal
from src.risk.risk_manager import RiskManager
from .gpt_controller import GPTController

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

    async def allow(self) -> bool:
        """Return ``True`` if a GPT call is permitted."""
        async with self._lock:
            if self._count >= self._max_per_hour:
                logging.warning("GPT call blocked: limit reached")
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
            return False

        if not await self.allow():
            return False

        response = self._controller.request_decision(
            list(candles)[-10:], position, self._risk_manager._params
        )
        if response is None:
            return False

        if not self._risk_manager.validate(response.size):
            logging.warning("GPT proposal rejected by risk manager")
            return False

        order = Order(asset=signal.asset, side=response.direction, quantity=response.size)
        return self._executor.place_order(order)
