# handlers/channel_tracker.py
from telegram import ChatMemberUpdated
from telegram.ext import ContextTypes
from db import add_channel, get_users_by_channel, remove_channel, get_user_channels

async def track_channels(update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
    chat = update.my_chat_member.chat
    status = update.my_chat_member.new_chat_member.status

    # Only proceed if the chat is a channel/supergroup
    if chat.type not in ["channel", "supergroup"]:
        return

    # Bot added as admin/creator
    if status in ["administrator", "creator"]:
        # Use the bot owner (the user who added it) if available
        owner_id = update.my_chat_member.from_user.id
        await add_channel(owner_id, chat.id, chat.title)
        print(f"Added channel {chat.title} ({chat.id}) for user {owner_id}")

    # Bot removed or kicked
    elif status in ["left", "kicked"]:
        # Remove by channel_id for all users who had it
        # This prevents stale entries if the original user_id doesn't match
        user_ids = await get_users_by_channel(chat.id)
        for uid in user_ids:
            await remove_channel(uid, chat.id)
        print(f"Removed channel {chat.title} ({chat.id}) from DB for all users")



