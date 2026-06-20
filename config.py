import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_OWNER_ID = os.getenv("BOT_OWNER_ID")

CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/bichniga")
DEEZLOAD_BOT = os.getenv("DEEZLOAD_BOT", "https://t.me/deezload2bot?start=")
