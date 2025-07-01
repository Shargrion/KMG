"""Execute trades through Binance API."""

import logging
from dataclasses import dataclass

from binance.client import Client
from binance.exceptions import BinanceAPIException


@dataclass
class Order:
    asset: str
    side: str
    quantity: float


class Executor:
    """Wrapper around Binance client."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        self._client = Client(api_key, api_secret)

    def place_order(self, order: Order) -> bool:
        try:
            logging.info("Placing order %s", order)
            self._client.create_order(
                symbol=order.asset,
                side=order.side,
                type="MARKET",
                quantity=order.quantity,
            )
            return True
        except BinanceAPIException as exc:
            logging.error("Order failed: %s", exc)
            return False
