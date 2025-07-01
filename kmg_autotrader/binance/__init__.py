import asyncio

class AsyncClient:
    @classmethod
    async def create(cls, *args, **kwargs):
        return cls()

    async def get_historical_klines(self, *args, **kwargs):
        return []

    async def close_connection(self):
        return None

class BinanceSocketManager:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def kline_socket(self, *args, **kwargs):
        class DummyStream:
            async def __aenter__(self):
                return self
            async def __aexit__(self, exc_type, exc, tb):
                pass
            async def __aiter__(self):
                return self
            async def __anext__(self):
                raise StopAsyncIteration
        return DummyStream()
