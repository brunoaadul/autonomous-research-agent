import os

from dotenv import load_dotenv


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()


def auth_is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)