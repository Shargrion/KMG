"""Tests for GPT controller and trigger validation."""

from typing import List

import pytest

from src.collector.binance_data_collector import Candle
from src.evaluator.rule_evaluator import Signal
from src.risk.risk_manager import RiskManager, RiskParameters
from src.trigger.gpt_controller import GPTController
from src.trigger.gpt_trigger import GPTTrigger


class DummyExecutor:
    def __init__(self) -> None:
        self.orders = []

    def place_order(self, order):  # type: ignore[override]
        self.orders.append(order)
        return True


@pytest.mark.asyncio
async def test_invalid_json(monkeypatch) -> None:
    def fake_create(*args, **kwargs):
        class R:
            choices = [type("obj", (), {"message": type("m", (), {"content": "not json"})()})]
        return R()

    monkeypatch.setattr(
        "src.trigger.gpt_controller.openai.ChatCompletion.create", fake_create
    )

    controller = GPTController(api_key="test")
    executor = DummyExecutor()
    risk = RiskManager(RiskParameters(1.0, 10.0))
    trigger = GPTTrigger(controller, risk, executor, max_per_hour=5)

    candles: List[Candle] = [Candle(0, 0, 0, 0, 0, 0, 0) for _ in range(10)]
    signal = Signal("BTC", "BUY", "reason", "rule")

    result = await trigger.process(signal, candles, 0.0)
    assert not result
    assert executor.orders == []


@pytest.mark.asyncio
async def test_risk_rejection(monkeypatch) -> None:
    def fake_create(*args, **kwargs):
        resp = {"direction": "BUY", "size": 2.0, "stop_loss": 1, "take_profit": 2, "confidence": 0.9}
        json_str = __import__("json").dumps(resp)

        class R:
            choices = [type("obj", (), {"message": type("m", (), {"content": json_str})()})]

        return R()

    monkeypatch.setattr(
        "src.trigger.gpt_controller.openai.ChatCompletion.create", fake_create
    )

    controller = GPTController(api_key="test")
    executor = DummyExecutor()
    risk = RiskManager(RiskParameters(1.0, 10.0))
    trigger = GPTTrigger(controller, risk, executor, max_per_hour=5)
    candles = [Candle(0, 0, 0, 0, 0, 0, 0) for _ in range(10)]
    signal = Signal("BTC", "BUY", "reason", "rule")

    result = await trigger.process(signal, candles, 0.0)
    assert not result
    assert executor.orders == []


@pytest.mark.asyncio
async def test_valid_order(monkeypatch) -> None:
    def fake_create(*args, **kwargs):
        resp = {"direction": "BUY", "size": 0.5, "stop_loss": 1, "take_profit": 2, "confidence": 0.9}
        json_str = __import__("json").dumps(resp)

        class R:
            choices = [type("obj", (), {"message": type("m", (), {"content": json_str})()})]

        return R()

    monkeypatch.setattr(
        "src.trigger.gpt_controller.openai.ChatCompletion.create", fake_create
    )

    controller = GPTController(api_key="test")
    executor = DummyExecutor()
    risk = RiskManager(RiskParameters(1.0, 10.0))
    trigger = GPTTrigger(controller, risk, executor, max_per_hour=5)
    candles = [Candle(0, 0, 0, 0, 0, 0, 0) for _ in range(10)]
    signal = Signal("BTC", "BUY", "reason", "rule")

    result = await trigger.process(signal, candles, 0.0)
    assert result
    assert len(executor.orders) == 1


@pytest.mark.asyncio
async def test_schema_fallback(monkeypatch) -> None:
    def fake_create(*args, **kwargs):
        resp = {"direction": "BUY", "size": 0.5, "stop_loss": 1, "confidence": 0.9}
        json_str = __import__("json").dumps(resp)

        class R:
            choices = [type("obj", (), {"message": type("m", (), {"content": json_str})()})]

        return R()

    monkeypatch.setattr(
        "src.trigger.gpt_controller.openai.ChatCompletion.create", fake_create
    )

    called = {"n": 0}

    def fake_rules(data):
        called["n"] += 1
        return []

    monkeypatch.setattr("src.trigger.gpt_controller.evaluate_rules", fake_rules)

    controller = GPTController(api_key="test")
    executor = DummyExecutor()
    risk = RiskManager(RiskParameters(1.0, 10.0))
    trigger = GPTTrigger(controller, risk, executor, max_per_hour=5)
    candles = [Candle(0, 0, 0, 0, 0, 0, 0) for _ in range(10)]
    signal = Signal("BTC", "BUY", "reason", "rule")

    result = await trigger.process(signal, candles, 0.0)
    assert not result
    assert called["n"] == 1
