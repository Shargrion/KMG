"""Main entry point for KMG-Autotrader."""

from __future__ import annotations

import asyncio
import logging

import uvicorn

from src.collector.binance_data_collector import BinanceDataCollector
from src.webui.backend import app


async def main() -> None:
    """Start the data collector and web server concurrently."""
    logging.basicConfig(level=logging.INFO)

    collector = BinanceDataCollector()
    server = uvicorn.Server(
        uvicorn.Config(app=app, host="0.0.0.0", port=8000, loop="asyncio")
    )

    collector_task = asyncio.create_task(collector.collect())
    server_task = asyncio.create_task(server.serve())

    await asyncio.gather(server_task, collector_task)


if __name__ == "__main__":
    asyncio.run(main())
