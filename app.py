from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.root.route import root
from routes.ws.route import ws

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
)

app.include_router(root)
app.include_router(ws)
