import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAPH_ACCESS_TOKEN = os.getenv("TELEGRAPH_ACCESS_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
if CHANNEL_ID:
    CHANNEL_ID = int(CHANNEL_ID)

CHANNEL_LINK = "https://t.me/bichniga"
DEEZLOAD_BOT = "http://t.me/deezload2bot?start="
