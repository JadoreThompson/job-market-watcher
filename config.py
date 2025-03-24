import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger()
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format="[%(levelname)s][%(asctime)s] %(name)s - %(funcName)s - %(message)s",
)

# Playwright
CANARY_USER_DATA_PATH = os.getenv("CANARY_USER_DATA_DIR")
CANARY_EXE_PATH = os.getenv("CANARY_EXEC_PATH")
