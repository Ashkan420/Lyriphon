"""Centralized configuration — loads environment variables and validates required ones."""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# --- Environment variables ---

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_OWNER_ID = os.getenv("BOT_OWNER_ID")

# --- Webhook configuration ---
# Public HTTPS base URL where Telegram will deliver updates (e.g. https://my-app.example.com).
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# Port to bind the webhook server to. PaaS platforms (Heroku, Render, ...) inject $PORT.
WEBHOOK_PORT = int(os.getenv("PORT", "8080"))
# Interface to listen on; 0.0.0.0 so the platform's router can reach it.
WEBHOOK_LISTEN = os.getenv("WEBHOOK_LISTEN", "0.0.0.0")
# Path component of the webhook endpoint (appended to WEBHOOK_URL).
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "webhook")
# Optional shared secret echoed back by Telegram in the X-Telegram-Bot-Api-Secret-Token
# header; PTB rejects requests that don't match it. Strongly recommended.
WEBHOOK_SECRET_TOKEN = os.getenv("WEBHOOK_SECRET_TOKEN")

# --- Validate required variables at import time ---

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

# --- External links ---

CHANNEL_LINK = "https://t.me/bichniga"
DEEZLOAD_BOT = "https://t.me/deezload2bot?start="
