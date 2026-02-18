from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import CHANNEL_ID

# escape special characters for MarkdownV2
def escape_md(text: str):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text


async def handle_music_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Automatically attaches the last created Telegraph page button
    to the next music file the user sends, without downloading.
    """

    music_msg = update.message

    # check if user has a recent telegraph
    track_name = context.user_data.get("last_track_name", "Unknown Track")
    artist_name = context.user_data.get("last_artist_name", "Unknown Artist")
    telegraph_url = context.user_data.get("last_telegraph")
    if not telegraph_url:
        return  # nothing to attach
    


    track_name_md = escape_md(track_name)
    artist_name_md = escape_md(artist_name)

    # Caption: monospace
    caption = f'`{track_name_md} — {artist_name_md}`'

    # Caption: quote first, then monospace
    #caption = f'> `"{track_name_md} — {artist_name_md}"`'

    # create inline button
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Lyrics", url=telegraph_url)]]
    )

    # attach button to the audio in the chat
    await context.bot.copy_message(
        chat_id=update.effective_chat.id,
        from_chat_id=music_msg.chat_id,
        message_id=music_msg.message_id,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=button
    )

    
    # store audio file_id for later sending to channel
    if music_msg.audio:
        context.user_data["pending_audio_file_id"] = music_msg.audio.file_id
        context.user_data["pending_caption"] = caption
        context.user_data["pending_telegraph_url"] = telegraph_url

    # ask if user wants to send to channel (only if channel id exists)
    if CHANNEL_ID:
        prompt = await update.message.reply_text(
            "Send to channel?",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ Yes", callback_data="send_to_channel")]]
            )
        )
        context.user_data["send_channel_prompt_id"] = prompt.message_id

    # clear user data so next file doesn't reuse old Telegraph
    context.user_data["last_telegraph"] = None
    context.user_data["last_track_name"] = None
    context.user_data["last_artist_name"] = None