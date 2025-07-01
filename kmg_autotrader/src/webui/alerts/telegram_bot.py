"""Send alerts via Telegram."""

import logging

from telegram import Bot


class TelegramBot:
    def __init__(self, token: str, chat_id: str) -> None:
        self._bot = Bot(token)
        self._chat_id = chat_id

    def send_message(self, text: str) -> None:
        try:
            self._bot.send_message(chat_id=self._chat_id, text=text)
        except Exception as exc:  # noqa: BLE001
            logging.error("Telegram send failed: %s", exc)
