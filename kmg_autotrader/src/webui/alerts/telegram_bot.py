"""Send alerts via Telegram."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Optional

try:  # requests may not be installed during tests
    import requests
except Exception:  # pragma: no cover - fallback
    requests = None  # type: ignore


@dataclass
class TelegramBot:
    """Simple wrapper around the Telegram Bot API."""

    token: str
    chat_id: str
    delay: float = 2.0
    _last_sent: float = 0.0

    @property
    def api_url(self) -> str:
        """Return the sendMessage endpoint for this bot."""

        return f"https://api.telegram.org/bot{self.token}/sendMessage"

    def send_message(self, text: str) -> None:
        """Send a message to the configured Telegram chat."""

        now = time.monotonic()
        if now - self._last_sent < self.delay:
            logging.debug("Skipping Telegram message to avoid spam")
            return

        self._last_sent = now
        if requests is None:
            logging.error("Requests library not installed; cannot send alert")
            return
        try:
            requests.post(
                self.api_url,
                data={"chat_id": self.chat_id, "text": text},
                timeout=5,
            )
            logging.debug("Sent Telegram message: %s", text)
        except Exception as exc:  # pragma: no cover - network errors
            logging.error("Telegram send failed: %s", exc)


_BOT: Optional[TelegramBot] = None


def _get_bot() -> Optional[TelegramBot]:
    """Instantiate :class:`TelegramBot` from environment settings."""

    global _BOT
    if _BOT is not None:
        return _BOT

    token = os.getenv("TELEGRAM_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        logging.debug("Telegram credentials missing; alerts disabled")
        return None

    _BOT = TelegramBot(token=token, chat_id=chat_id)
    return _BOT


def send_alert(message: str) -> None:
    """Send a Telegram alert using configuration from ``.env``."""

    bot = _get_bot()
    if bot is None:
        return
    bot.send_message(message)
