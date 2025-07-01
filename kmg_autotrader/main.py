"""Main entry point for KMG-Autotrader."""

import asyncio
import logging

from src.collector.binance_data_collector import BinanceDataCollector


async def main() -> None:
    """Start the trading system."""
    logging.basicConfig(level=logging.INFO)
    collector = BinanceDataCollector()
    await collector.collect()


if __name__ == "__main__":
    asyncio.run(main())
