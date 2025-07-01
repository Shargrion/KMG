"""Main entry point for KMG-Autotrader."""

from __future__ import annotations

import asyncio
import logging
import os
import signal

import asyncpg
import uvicorn
from dotenv import load_dotenv

from src.analysis import ml_trainer, performance_analyzer
from src.collector.binance_data_collector import BinanceDataCollector
from src.trigger.gpt_trigger import GPTTrigger
from src.webui.backend import app
from scheduler import start_scheduler


async def init_db() -> None:
    """Ensure database connection is available."""
    db_url = os.getenv("POSTGRES_URL")
    if not db_url:
        logging.error("POSTGRES_URL is not configured")
        return
    conn = await asyncpg.connect(db_url)
    await conn.close()
    logging.info("Database connection initialized")


async def main() -> None:
    """Start all services and handle graceful shutdown."""
    logging.basicConfig(level=logging.INFO)
    load_dotenv()

    await init_db()

    gpt_trigger = GPTTrigger(int(os.getenv("GPT_CALL_LIMIT_PER_HOUR", "10")))
    scheduler = start_scheduler(gpt_trigger, ml_trainer, performance_analyzer)

    collector = BinanceDataCollector()
    server = uvicorn.Server(
        uvicorn.Config(app=app, host="0.0.0.0", port=8000, loop="asyncio")
    )

    collector_task = asyncio.create_task(collector.collect())
    server_task = asyncio.create_task(server.serve())

    stop_event = asyncio.Event()

    def _handle_stop(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, _handle_stop)
    loop.add_signal_handler(signal.SIGTERM, _handle_stop)

    await stop_event.wait()
    logging.info("Shutdown signal received")

    scheduler.shutdown()
    collector_task.cancel()
    server.should_exit = True

    await asyncio.gather(server_task, return_exceptions=True)
    await asyncio.gather(collector_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
