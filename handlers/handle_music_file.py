from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from handlers.escape_md import escape_md
from db import get_user_channels



async def handle_music_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Automatically attaches the last created Telegraph page button
    to the next music file the user sends, without downloading.
    """

    music_msg = update.message

    telegraph_url = context.user_data.get("last_telegraph")
    last_data = context.user_data.get("last_telegraph_data")

    if not telegraph_url or not last_data:
        return  # nothing to attach

    # Always use updated values
    track_name = last_data.get("track", "Unknown Track")
    artist_name = last_data.get("artist", "Unknown Artist")

    track_name_md = escape_md(track_name)
    artist_name_md = escape_md(artist_name)


    # create inline button
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Lyrics", url=telegraph_url)]]
    )

    # add invisible telegraph link to caption
    hidden_link = f"[‎]({telegraph_url})"

    # Caption: monospace
    #caption = f'`{track_name_md} — {artist_name_md}`'

    # Caption: quote first, then monospace, with hidden link
    caption = f'>`{track_name_md} — {artist_name_md}`{hidden_link}'

    #caption = caption + hidden_link

    # attach button to the audio in the chat
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=music_msg.chat_id,
        message_id=music_msg.message_id,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=button,
    )

    # store audio file_id for later sending to channel
    if music_msg.audio:
        context.user_data["pending_audio_file_id"] = music_msg.audio.file_id
        context.user_data["pending_caption"] = caption
        context.user_data["pending_telegraph_url"] = telegraph_url

    # Instead of CHANNEL_ID
    user_channels = await get_user_channels(update.effective_user.id)
    # Filter out channels that no longer exist in the DB (optional sanity check)
    if user_channels:
        buttons = [
            [InlineKeyboardButton(title, callback_data=f"send_channel_{chat_id}")]
            for chat_id, title in user_channels.items()
        ]
        prompt = await update.message.reply_text(
            "Send to which channel?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        context.user_data["send_channel_prompt_id"] = prompt.message_id

    # clear telegraph so next file doesn't reuse old Telegraph
    context.user_data["last_telegraph"] = None
