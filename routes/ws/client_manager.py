import asyncio
from typing import List, Literal
from fastapi import WebSocket
from config import INDUSTRY_BAR_CHART_KEY_LIVE, PLANG_BAR_CHART_KEY_LIVE, REDIS_CLIENT


class ClientManger:
    def __init__(self) -> None:
        self._plang_connections: List[WebSocket] = []
        self._industry_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()
        self._is_running: bool = False

    async def _init(self):
        asyncio.create_task(self._listen_plang_bar_chart())
        asyncio.create_task(self._listen_industry_bar_chart())

    async def connect(
        self, ws: WebSocket, channel: Literal["plang", "industry"]
    ) -> None:
        if not self._is_running:
            await self._init()
            self._is_running = True

        async with self._lock:
            if channel == "plang":
                self._plang_connections.append(ws)
            else:
                self._industry_connections.append(ws)

    async def disconnect(
        self, ws: WebSocket, channel: Literal["plang", "industry"]
    ) -> None:
        async with self._lock:
            if channel == "plang":
                self._plang_connections.remove(ws)
            else:
                self._industry_connections.remove(ws)

    async def _listen_plang_bar_chart(self) -> None:
        async with REDIS_CLIENT.pubsub() as ps:
            await ps.subscribe(PLANG_BAR_CHART_KEY_LIVE)
            async for message in ps.listen():
                if message["type"] == "message":
                    async with self._lock:
                        for ws in self._plang_connections:
                            try:
                                await ws.send_bytes(message["data"])
                            except RuntimeError:
                                await ws.close()

    async def _listen_industry_bar_chart(self) -> None:
        async with REDIS_CLIENT.pubsub() as ps:
            await ps.subscribe(INDUSTRY_BAR_CHART_KEY_LIVE)
            async for message in ps.listen():
                if message["type"] == "message":
                    async with self._lock:
                        for ws in self._industry_connections:
                            try:
                                await ws.send_bytes(message["data"])
                            except RuntimeError:
                                await ws.close()
