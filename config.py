import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

_REQUIRED = {
    "BOT_TOKEN": BOT_TOKEN,
    "TELEGRAPH_ACCESS_TOKEN": TELEGRAPH_ACCESS_TOKEN,
    "DATABASE_URL": DATABASE_URL,
}
_missing = [name for name, val in _REQUIRED.items() if not val]
if _missing:
    raise RuntimeError(
        f"Missing required environment variable(s): {', '.join(_missing)}. "
        "Check your .env file."
    )


CHANNEL_LINK = "https://t.me/bichniga"
DEEZLOAD_BOT = "http://t.me/deezload2bot?start="
