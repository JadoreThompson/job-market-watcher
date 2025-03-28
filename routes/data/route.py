from fastapi import APIRouter, WebSocket
from .client_manager import ClientManger

data = APIRouter(prefix="/data", tags=["data"])
manager = ClientManger()


@data.websocket("/ws/programming-languages")
async def programming_languages(ws: WebSocket):
    await ws.accept()
    await manager.connect(ws, "plang")

    try:
        while True:
            await ws.receive()
    finally:
        manager.disconnect(ws, "plang")


@data.websocket("/ws/industries")
async def programming_languages(ws: WebSocket):
    await ws.accept()
    await manager.connect(ws, "industry")

    try:
        while True:
            await ws.receive()
    finally:
        manager.disconnect(ws, "industry")
