"""Track bot membership in channels — registers/removes from DB on admin add/remove."""

import logging
from telegram import ChatMemberUpdated
from telegram.ext import ContextTypes
from db import add_channel, get_users_by_channel, remove_channel, get_user_channels

logger = logging.getLogger(__name__)

async def track_channels(update: ChatMemberUpdated, context: ContextTypes.DEFAULT_TYPE):
    """React to the bot being added or removed from a channel/supergroup."""
    chat = update.my_chat_member.chat
    status = update.my_chat_member.new_chat_member.status

    # Only proceed if the chat is a channel/supergroup
    if chat.type not in ["channel", "supergroup"]:
        return

    # Bot added as admin/creator
    if status in ["administrator", "creator"]:
        owner_id = update.my_chat_member.from_user.id
        try:
            await add_channel(owner_id, chat.id, chat.title)
            logger.info("Added channel %s (%s) for user %s", chat.title, chat.id, owner_id)
        except Exception:
            logger.exception("Failed to add channel %s (%s) for user %s", chat.title, chat.id, owner_id)

    # Bot removed or kicked
    elif status in ["left", "kicked"]:
        try:
            user_ids = await get_users_by_channel(chat.id)
            for uid in user_ids:
                await remove_channel(uid, chat.id)
            logger.info("Removed channel %s (%s) from DB for all users", chat.title, chat.id)
        except Exception:
            logger.exception("Failed to remove channel %s (%s) from DB", chat.title, chat.id)



