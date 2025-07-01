from unittest import mock
"""Tests for trade executor using mocked Binance API."""

import pytest

from src.executor.executor import Executor
from src.binance_client import BinanceAPIException
from src.trigger.gpt_controller import GPTResponse


def make_response(size: float = 0.1) -> GPTResponse:
    return GPTResponse(
        direction="BUY",
        size=size,
        stop_loss=1.0,
        take_profit=2.0,
        confidence=0.9,
    )


def setup_executor(monkeypatch: pytest.MonkeyPatch, client_mock: mock.Mock) -> Executor:
    controller = mock.Mock()
    controller.send_prompt.return_value = make_response()
    return Executor(client=client_mock, gpt=controller, db_path=":memory:", position_limit=0.2)


def test_successful_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    client = mock.Mock()
    client.get_position.return_value = 0.0
    client.place_order.return_value = {"price": "100"}
    executor = setup_executor(monkeypatch, client)

    assert executor.execute("prompt", "BTCUSDT")
    client.place_order.assert_called_once()
    rows = executor._conn.execute("SELECT COUNT(*) FROM TradeLog").fetchone()[0]
    assert rows == 1


def test_execution_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = mock.Mock()
    client.get_position.return_value = 0.0
    client.place_order.side_effect = BinanceAPIException("error")
    executor = setup_executor(monkeypatch, client)

    assert not executor.execute("prompt", "BTCUSDT")
    rows = executor._conn.execute("SELECT status FROM TradeLog").fetchall()
    assert rows[0][0] == "error"


def test_position_limit_reject(monkeypatch: pytest.MonkeyPatch) -> None:
    client = mock.Mock()
    client.get_position.return_value = 0.15
    client.place_order.return_value = {"price": "100"}
    controller = mock.Mock()
    controller.send_prompt.return_value = make_response(0.1)
    executor = Executor(client=client, gpt=controller, db_path=":memory:", position_limit=0.2)

    assert not executor.execute("prompt", "BTCUSDT")
    client.place_order.assert_not_called()
    rows = executor._conn.execute("SELECT status FROM TradeLog").fetchall()
    assert rows[0][0] == "rejected"
