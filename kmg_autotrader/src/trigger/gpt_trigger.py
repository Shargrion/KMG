"""Manage GPT invocation frequency and scheduling."""

import asyncio
from typing import Callable


class GPTTrigger:
    """Rate-limited trigger for GPT requests."""

    def __init__(self, max_per_hour: int) -> None:
        self._max_per_hour = max_per_hour
        self._count = 0
        self._lock = asyncio.Lock()

    async def allow(self) -> bool:
        async with self._lock:
            if self._count >= self._max_per_hour:
                return False
            self._count += 1
            return True

    async def reset(self) -> None:
        """Reset counter every hour."""
        while True:
            await asyncio.sleep(3600)
            async with self._lock:
                self._count = 0
