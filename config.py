import os
import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
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


# Playwright
CANARY_USER_DATA_PATH = os.getenv("CANARY_USER_DATA_DIR")
CANARY_EXE_PATH = os.getenv("CANARY_EXEC_PATH")

# LLM
LLM_API_KEY = os.getenv("MISTRAL_API_KEY")
LLM_BASE_URL = os.getenv("MISTRAL_BASE_URL")
