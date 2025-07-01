"""Tests for BinanceDataCollector."""

import asyncio
from unittest import mock

import pytest

from src.collector.binance_data_collector import BinanceDataCollector


def test_collect(monkeypatch: pytest.MonkeyPatch) -> None:
    collector = BinanceDataCollector()

    async def dummy(*args, **kwargs):
        return None

    monkeypatch.setattr(collector, "_connect", dummy)
    monkeypatch.setattr(collector, "_fetch_historical", dummy)
    monkeypatch.setattr(collector, "_start_ws", dummy)

    asyncio.run(collector.collect())
