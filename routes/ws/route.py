from fastapi import APIRouter, WebSocket
from .client_manager import ClientManger

ws = APIRouter(prefix="/ws", tags=["ws"])
manager = ClientManger()


@ws.websocket("/programming-languages")
async def programming_languages_ws(ws: WebSocket):
    await ws.accept()
    await manager.connect(ws, "plang")

    try:
        while True:
            await ws.receive()
    except RuntimeError:
        pass
    finally:
        await manager.disconnect(ws, "plang")


@ws.websocket("/industries")
async def industries_ws(ws: WebSocket):
    await ws.accept()
    await manager.connect(ws, "industry")

    try:
        while True:
            await ws.receive()
    except RuntimeError:
        pass
    finally:
        await manager.disconnect(ws, "industry")
