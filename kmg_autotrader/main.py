"""Main entry point for KMG-Autotrader."""

from __future__ import annotations

import asyncio
import logging
import os

import uvicorn

from src.analysis import ml_trainer, performance_analyzer
from src.collector.binance_data_collector import BinanceDataCollector
from src.executor.executor import Executor
from src.risk.risk_manager import RiskManager, RiskParameters
from src.scheduler import Scheduler
from src.trigger.gpt_controller import GPTController
from src.trigger.gpt_trigger import GPTTrigger
from src.webui.backend import app


async def main() -> None:
    """Start components and run until terminated."""

    logging.basicConfig(level=logging.INFO)

    # Database initialization happens on module import
    _ = performance_analyzer.SessionLocal

    collector = BinanceDataCollector()

    controller = GPTController(api_key=os.getenv("OPENAI_API_KEY", ""))
    risk = RiskManager(
        RiskParameters(
            max_position_percent=float(os.getenv("MAX_POSITION_PERCENT", "0.2")),
            max_drawdown=float(os.getenv("MAX_DRAWDOWN", "5.0")),
        )
    )
    executor = Executor()
    trigger = GPTTrigger(
        controller,
        risk,
        executor,
        int(os.getenv("GPT_CALL_LIMIT_PER_HOUR", "10")),
    )

    scheduler = Scheduler(trigger, ml_trainer, performance_analyzer)
    scheduler.start()

    server = uvicorn.Server(
        uvicorn.Config(app=app, host="0.0.0.0", port=8000, loop="asyncio")
    )

    collector_task = asyncio.create_task(collector.collect())
    server_task = asyncio.create_task(server.serve())

    try:
        await asyncio.gather(server_task, collector_task)
    finally:
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
