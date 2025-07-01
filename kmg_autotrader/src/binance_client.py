"""Binance API wrapper using python-binance."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

try:  # python-dotenv might not be available in minimal environments
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - fallback when dependency missing
    def load_dotenv() -> None:
        """Fallback no-op for load_dotenv."""
        pass

try:
    from binance.client import Client  # type: ignore
    from binance.exceptions import BinanceAPIException  # type: ignore
except Exception:  # pragma: no cover - fallback if library missing
    class BinanceAPIException(Exception):
        """Fallback API exception when python-binance is unavailable."""

    class Client:  # pragma: no cover - very small stub
        ORDER_TYPE_MARKET = "MARKET"
        ORDER_TYPE_LIMIT = "LIMIT"

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def create_order(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore
            raise BinanceAPIException("client not implemented")

        def get_account(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore
            return {"balances": []}

        def get_asset_balance(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore
            return {"free": "0"}

        def cancel_order(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore
            return {}


load_dotenv()


def _get_env(key: str) -> str:
    value = os.getenv(key)
    if value is None:
        raise RuntimeError(f"Environment variable {key} not set")
    return value


@dataclass
class BinanceClient:
    """Simple synchronous client for interacting with Binance."""

    api_key: str | None = None
    api_secret: str | None = None

    def __post_init__(self) -> None:
        if self.api_key is None:
            self.api_key = _get_env("BINANCE_API_KEY")
        if self.api_secret is None:
            self.api_secret = _get_env("BINANCE_SECRET_KEY")
        self._client = Client(self.api_key, self.api_secret)
        logging.debug("BinanceClient initialized")

    # ------------------------------------------------------------------
    # basic wrappers around python-binance Client methods
    # ------------------------------------------------------------------
    def place_order(
        self, symbol: str, side: str, qty: float, price: float | None = None
    ) -> Dict[str, Any]:
        """Place a market or limit order."""
        order_type = Client.ORDER_TYPE_LIMIT if price else Client.ORDER_TYPE_MARKET
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": qty,
        }
        if price:
            params["price"] = price
        logging.debug("Sending order to Binance: %s", params)
        return self._client.create_order(**params)

    def get_position(self, symbol: str) -> float:
        """Return free balance for the given asset."""
        asset = symbol
        try:
            data = self._client.get_asset_balance(asset=asset)
            return float(data.get("free", 0))
        except BinanceAPIException as exc:  # pragma: no cover - network errors
            logging.error("Failed to fetch position: %s", exc)
            return 0.0

    def get_balance(self) -> Dict[str, float]:
        """Return account balances as a mapping."""
        try:
            account = self._client.get_account()
            return {b["asset"]: float(b["free"]) for b in account.get("balances", [])}
        except BinanceAPIException as exc:  # pragma: no cover
            logging.error("Failed to fetch balance: %s", exc)
            return {}

    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an existing order."""
        try:
            return self._client.cancel_order(symbol=symbol, orderId=order_id)
        except BinanceAPIException as exc:  # pragma: no cover
            logging.error("Cancel order failed: %s", exc)
            raise
