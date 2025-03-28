from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.data.route import data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
    allow_credentials=True,
)

app.include_router(data)
