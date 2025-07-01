"""High level trade executor interacting with Binance."""

from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:  # python-dotenv may not be installed during tests
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback
    def load_dotenv() -> None:
        pass

from src.binance_client import BinanceClient, BinanceAPIException
from src.trigger.gpt_controller import GPTController, GPTResponse

load_dotenv()


@dataclass
class Order:
    """Representation of a trade order."""

    asset: str
    side: str
    quantity: float
    price: float | None = None


class Executor:
    """Execute GPT-driven orders with risk checks and logging."""

    def __init__(
        self,
        client: BinanceClient | None = None,
        gpt: GPTController | None = None,
        db_path: str | None = None,
        position_limit: float | None = None,
    ) -> None:
        self._client = client or BinanceClient()
        api_key = os.getenv("OPENAI_API_KEY", "")
        self._gpt = gpt or GPTController(api_key=api_key)
        self._position_limit = (
            position_limit if position_limit is not None else float(os.getenv("POSITION_LIMIT_PERCENT", "0.2"))
        )
        path = (
            Path(db_path)
            if db_path
            else Path(__file__).resolve().parents[2]
            / "project_metadata"
            / "trade_log.db"
        )
        self._conn = sqlite3.connect(path)
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS TradeLog(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                quantity REAL,
                price REAL,
                status TEXT
            )
            """
        )
        self._conn.commit()
        self._retry_timeout = 5.0
        logging.debug("Executor initialized with limit %.2f", self._position_limit)

    # ------------------------------------------------------------------
    def _log_trade(
        self, symbol: str, side: str, qty: float, price: float, status: str
    ) -> None:
        self._conn.execute(
            "INSERT INTO TradeLog(timestamp, symbol, side, quantity, price, status) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat(), symbol, side, qty, price, status),
        )
        self._conn.commit()

    def _call_with_retry(self, func, *args, **kwargs):
        end = time.time() + self._retry_timeout
        while True:
            try:
                return func(*args, **kwargs)
            except BinanceAPIException as exc:
                if time.time() >= end:
                    logging.error("Retries exhausted: %s", exc)
                    raise
                logging.warning("Binance error, retrying: %s", exc)
                time.sleep(1)

    # ------------------------------------------------------------------
    def execute(self, prompt: str, symbol: str) -> bool:
        """Get GPT signal and place order if within limits."""
        signal: GPTResponse | None = self._gpt.send_prompt(prompt)
        if signal is None:
            logging.error("GPT returned no signal")
            return False

        current = self._client.get_position(symbol)
        if current + signal.size > self._position_limit:
            logging.warning("Position limit exceeded for %s", symbol)
            self._log_trade(symbol, signal.direction, signal.size, 0.0, "rejected")
            return False

        order = Order(asset=symbol, side=signal.direction, quantity=signal.size)
        try:
            result = self._call_with_retry(
                self._client.place_order,
                symbol,
                signal.direction,
                signal.size,
            )
            price = 0.0
            if isinstance(result, dict):
                price = float(result.get("price", 0) or result.get("fills", [{}])[0].get("price", 0))
            self._log_trade(symbol, signal.direction, signal.size, price, "filled")
            return True
        except BinanceAPIException as exc:
            logging.error("Order failed: %s", exc)
            self._log_trade(symbol, signal.direction, signal.size, 0.0, "error")
            return False
