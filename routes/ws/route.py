from fastapi import APIRouter, WebSocket
from .client_manager import ClientManger

ws = APIRouter(prefix="/ws", tags=["ws"])
manager = ClientManger()


@ws.websocket("/programming-languages")
async def programming_languages_ws(ws: WebSocket):
    print(1)
    await ws.accept()
    print(2)
    await manager.connect(ws, "plang")
    print(3)

    try:
        while True:
            print(4)
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
