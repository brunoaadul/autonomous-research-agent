import os

from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def auth_is_configured() -> bool:
    return bool(DATABASE_URL)