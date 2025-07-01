"""Manage GPT invocation frequency and scheduling."""

import asyncio
import logging


class GPTTrigger:
    """Rate-limited trigger for GPT requests."""

    def __init__(self, max_per_hour: int) -> None:
        """Create a new trigger with a maximum number of calls per hour."""
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

    async def check_new_signals(self) -> None:
        """Placeholder to check and process new trading signals."""
        logging.info("Checking for new GPT signals")
        await self.allow()
