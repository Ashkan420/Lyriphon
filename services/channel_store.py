# handlers/channel_store.py
import json
import os

FILE_PATH = "data/channels.json"

def load_channels():
    if not os.path.exists(FILE_PATH):
        return {}
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_channels(channels: dict):
    os.makedirs("data", exist_ok=True)
    with open(FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4, ensure_ascii=False)

def add_channel(user_id: int, chat_id: int, title: str):
    channels = load_channels()
    channels.setdefault(str(user_id), {})
    channels[str(user_id)][str(chat_id)] = title
    save_channels(channels)

def remove_channel(user_id: int, chat_id: int):
    channels = load_channels()
    user_channels = channels.get(str(user_id), {})
    user_channels.pop(str(chat_id), None)
    channels[str(user_id)] = user_channels
    save_channels(channels)

def get_user_channels(user_id: int):
    channels = load_channels()
    return channels.get(str(user_id), {})
