"""Binance data collector for historical and live market data."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Iterable

import asyncpg
from binance import AsyncClient, BinanceSocketManager


@dataclass
class Candle:
    """Single OHLCV candle."""

    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int


class BinanceDataCollector:
    """Collects data from Binance and stores it in PostgreSQL."""

    def __init__(self, symbol: str = "BTCUSDT", interval: str = "1m") -> None:
        """Initialize the collector with trading pair and candle interval."""
        self._symbol = symbol
        self._interval = interval
        self._db_url = os.getenv("POSTGRES_URL")
        self._client: AsyncClient | None = None
        self._conn: asyncpg.Connection | None = None

    async def _connect(self) -> None:
        self._client = await AsyncClient.create()
        self._conn = await asyncpg.connect(self._db_url)
        await self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS market_data (
                open_time BIGINT PRIMARY KEY,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                volume DOUBLE PRECISION,
                close_time BIGINT
            )
            """
        )

    async def _fetch_historical(self) -> None:
        assert self._client
        logging.info("Fetching historical data for %s", self._symbol)
        klines = await self._client.get_historical_klines(
            self._symbol,
            self._interval,
            "1 year ago UTC",
        )
        await self._bulk_insert(klines)

    async def _bulk_insert(self, klines: Iterable[list[Any]]) -> None:
        assert self._conn
        records = [
            (
                int(k[0]),
                float(k[1]),
                float(k[2]),
                float(k[3]),
                float(k[4]),
                float(k[5]),
                int(k[6]),
            )
            for k in klines
        ]
        await self._conn.executemany(
            """
            INSERT INTO market_data(open_time, open, high, low, close, volume, close_time)
            VALUES($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (open_time) DO NOTHING
            """,
            records,
        )

    async def _start_ws(self) -> None:
        assert self._client
        assert self._conn
        logging.info("Starting websocket stream for %s", self._symbol)
        bm = BinanceSocketManager(self._client)
        async with bm.kline_socket(self._symbol, interval=self._interval) as stream:
            async for message in stream:
                data = message["k"]
                candle = (
                    int(data["t"]),
                    float(data["o"]),
                    float(data["h"]),
                    float(data["l"]),
                    float(data["c"]),
                    float(data["v"]),
                    int(data["T"]),
                )
                await self._bulk_insert([candle])

    async def collect(self) -> None:
        """Collect historical and real-time data then close connections."""
        await self._connect()
        try:
            await self._fetch_historical()
            await self._start_ws()
        finally:
            if self._client:
                await self._client.close_connection()
            if self._conn:
                await self._conn.close()
