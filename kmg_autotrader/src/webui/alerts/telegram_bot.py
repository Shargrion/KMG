"""Send alerts via Telegram."""

import logging

from telegram import Bot


class TelegramBot:
    """Simple wrapper around the Telegram Bot API."""

    def __init__(self, token: str, chat_id: str) -> None:
        """Create the bot with the provided credentials."""
        self._bot = Bot(token)
        self._chat_id = chat_id

    def send_message(self, text: str) -> None:
        """Send a message to the configured Telegram chat."""
        try:
            self._bot.send_message(chat_id=self._chat_id, text=text)
            logging.debug("Sent Telegram message: %s", text)
        except Exception as exc:  # noqa: BLE001
            logging.error("Telegram send failed: %s", exc)
