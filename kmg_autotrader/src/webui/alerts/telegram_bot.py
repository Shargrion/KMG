"""Send alerts via Telegram."""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

import requests


class TelegramBot:
    """Simple wrapper around the Telegram Bot API."""

    def __init__(self, token: str, chat_id: str, delay: int = 5) -> None:
        """Create the bot with the provided credentials."""
        self._token = token
        self._chat_id = chat_id
        self._delay = delay
        self._last_sent = 0.0

    def send_message(self, text: str) -> None:
        """Send a message to the configured Telegram chat."""
        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        now = time.time()
        if now - self._last_sent < self._delay:
            logging.debug("Skipping Telegram alert to avoid spam")
            return
        try:
            requests.post(url, data={"chat_id": self._chat_id, "text": text}, timeout=10)
            self._last_sent = now
            logging.debug("Sent Telegram message: %s", text)
        except Exception as exc:  # noqa: BLE001
            logging.error("Telegram send failed: %s", exc)


_bot: Optional[TelegramBot] = None


def send_alert(message: str) -> None:
    """Send an alert using credentials from environment variables."""
    global _bot
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logging.warning("Telegram credentials not configured")
        return

    if _bot is None:
        _bot = TelegramBot(token, chat_id)

    _bot.send_message(message)
