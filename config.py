import os
import logging

from dotenv import load_dotenv
from redis.asyncio import Redis, ConnectionPool, Connection
from sqlalchemy.ext.asyncio import create_async_engine
from typing import Optional
from urllib.parse import quote

load_dotenv()

logger = logging.getLogger()
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="[%(levelname)s][%(asctime)s] %(name)s - %(funcName)s - %(message)s",
)

# DB
DB_URL = f"postgresql+asyncpg://{os.getenv("DB_USER")}:{quote(os.getenv("DB_PASSWORD"))}@{os.getenv("DB_HOST")}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
DB_ENGINE = create_async_engine(
    DB_URL,
    future=True,
    echo_pool=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=6000,
)

# LLM
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

# Playwright
CANARY_USER_DATA_PATH = os.getenv("CANARY_USER_DATA_DIR")
CANARY_EXE_PATH = os.getenv("CANARY_EXEC_PATH")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = int(os.getenv("REDIS_PORT"))
REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")

REDIS_CLIENT = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    max_connections=20,
    decode_responses=True,
    connection_pool=ConnectionPool(
        connection_class=Connection,
        max_connections=20,
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
    ),
)

CLEANED_DATA_KEY = os.getenv("CLEANED_DATA_KEY")
BAR_CHART_KEY = os.getenv("BAR_CHART_KEY")
