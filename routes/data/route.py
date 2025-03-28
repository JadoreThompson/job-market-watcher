from fastapi import APIRouter, WebSocket
from .client_manager import ClientManger

data = APIRouter(prefix="/data", tags=["data"])
manager = ClientManger()


@data.websocket("/ws/programming-languages")
async def programming_languages(ws: WebSocket): ...
