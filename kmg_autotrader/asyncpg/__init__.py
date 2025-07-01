import asyncio

class Connection:
    async def execute(self, *args, **kwargs):
        return None

    async def executemany(self, *args, **kwargs):
        return None

    async def close(self):
        return None

async def connect(*args, **kwargs):
    return Connection()
