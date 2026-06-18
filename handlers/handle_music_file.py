from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from handlers.escape_md import escape_md
from db import get_user_channels
from services.deezer_api import search_tracks
from handlers.song_search import build_track_buttons



async def handle_music_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle audio files:
    1. If user has a pending Telegraph, attach it to the audio
    2. Otherwise, auto-trigger search flow
    """

    music_msg = update.message

    # Handle media groups (multiple audio messages)
    if music_msg.media_group_id:
        # Check if this is a new media group or continuation
        if context.user_data.get("current_media_group") == music_msg.media_group_id:
            return
        
        # New media group - reject it
        context.user_data["current_media_group"] = music_msg.media_group_id
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Please send only one music file at a time."
        )
        return

    # Extract metadata from audio
    title = music_msg.audio.title if music_msg.audio and music_msg.audio.title else None
    artist = music_msg.audio.performer if music_msg.audio and music_msg.audio.performer else None
    filename = music_msg.audio.file_name if music_msg.audio and music_msg.audio.file_name else "Unknown"

    if not title:
        title = filename.rsplit(".", 1)[0] if "." in filename else filename
    if not artist:
        artist = "Unknown"

    # Case 1: User has a pending Telegraph - attach it to this audio
    telegraph_url = context.user_data.get("last_telegraph")
    last_data = context.user_data.get("last_telegraph_data")

    if telegraph_url and last_data:
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

        # Caption: quote first, then monospace, with hidden link
        caption = f'>`{track_name_md} — {artist_name_md}`{hidden_link}'

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
        return

    # Case 2: No pending Telegraph - auto-trigger search flow
    # Check if user is in edit mode
    if context.user_data.get("edit_mode"):
        return

    # Store pending audio session
    context.user_data["pending_audio"] = {
        "file_id": music_msg.audio.file_id if music_msg.audio else None,
        "title": title,
        "artist": artist,
        "mode": "auto_audio_flow",
        "message_id": music_msg.message_id
    }

    # Auto-trigger search
    search_query = f"{artist} {title}"
    results = await search_tracks(search_query)

    if results is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Search failed. Try again later."
        )
        context.user_data["pending_audio"] = None
        return

    if not results:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ No results found."
        )
        context.user_data["pending_audio"] = None
        return

    context.user_data["song_search_results"] = results
    context.user_data["song_search_page"] = 0

    buttons = build_track_buttons(results, page=0)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🎵 Found matches for: {artist} - {title}\nSelect the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
