import os
from dotenv import load_dotenv

load_dotenv()

CANARY_USER_DATA_PATH = os.getenv("CANARY_USER_DATA_DIR")
CANARY_EXE_PATH = os.getenv("CANARY_EXEC_PATH")
