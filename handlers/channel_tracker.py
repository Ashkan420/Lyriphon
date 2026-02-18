# handlers/channel_tracker.py
from telegram import ChatMemberUpdated
from telegram.ext import ContextTypes
import services.channel_store as store

async def track_channels(update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
    chat = update.my_chat_member.chat
    user_id = update.my_chat_member.from_user.id  # the user who added the bot
    status = update.my_chat_member.new_chat_member.status

    # Bot added as admin/creator -> save channel for that user
    if status in ["administrator", "creator"]:
        store.add_channel(user_id, chat.id, chat.title)

    # Bot removed or kicked -> remove channel for that user
    elif status in ["left", "kicked"]:
        store.remove_channel(user_id, chat.id)
