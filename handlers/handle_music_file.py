from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
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
        await update.message.reply_text(
            "❌ Please send only one music file at a time."
        )
        return

    # Extract metadata from audio
    title = music_msg.audio.title if music_msg.audio and music_msg.audio.title else None
    artist = music_msg.audio.performer if music_msg.audio and music_msg.audio.performer else None
    filename = music_msg.audio.file_name if music_msg.audio and music_msg.audio.file_name else "Unknown"

    if not title:
        title = filename.rsplit(".", 1)[0] if "." in filename else filename
    if not artist:
        artist = ""

    # Parse common filename patterns for better metadata
    if " - " in title:
        parts = title.split(" - ", 1)
        artist = artist or parts[0].strip()
        title = parts[1].strip()
    elif " – " in title:
        parts = title.split(" – ", 1)
        artist = artist or parts[0].strip()
        title = parts[1].strip()
    elif "_-_" in title:
        parts = title.split("_-_", 1)
        artist = artist or parts[0].strip()
        title = parts[1].strip()

    # Case 1: User has a pending Telegraph - show decision menu
    telegraph_url = context.user_data.get("last_telegraph")
    last_data = context.user_data.get("last_telegraph_data")

    if telegraph_url and last_data and not context.user_data.get("pending_audio") and not context.user_data.get("editing_session_active"):
        # Store audio info for the decision callback
        context.user_data["pending_audio_decision"] = {
            "file_id": music_msg.audio.file_id if music_msg.audio else None,
            "message_id": music_msg.message_id,
            "title": title,
            "artist": artist,
        }

        decision_buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("📎 Attach to Current Telegraph", callback_data="audio_decision_attach")],
            [InlineKeyboardButton("🔍 Search Using This File", callback_data="audio_decision_search")],
            [InlineKeyboardButton("❌ Cancel", callback_data="audio_decision_cancel")],
        ])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🎵 What would you like to do with this file?",
            reply_markup=decision_buttons,
        )
        return

    # Case 2: No pending Telegraph - auto-trigger search flow
    # Check if user is in edit mode
    if context.user_data.get("editing_session_active"):
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
    search_query = f"{artist} {title}".strip()
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
        text=f"🎵 Found matches for: {artist} - {title}\nSelect the track:" if artist else f"🎵 Found matches for: {title}\nSelect the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
