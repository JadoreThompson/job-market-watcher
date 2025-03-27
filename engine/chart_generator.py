import asyncio
from config import BAR_CHART_KEY, CLEANED_DATA_KEY, REDIS_CLIENT


class ChartGenerator:
    def __init__(self) -> None:
        pass

    async def run(self) -> None:
        await self._listen()

    async def _listen(self) -> None:
        async with REDIS_CLIENT.pubsub() as ps:
            await ps.subscribe(CLEANED_DATA_KEY)

            async for message in ps.listen():
                if message["type"] == "message":
                    await self._generate_bar_chart(message["data"])

    async def _generate_bar_chart(self, data) -> None:
        print("[chart_generator] ", data)
        pass
