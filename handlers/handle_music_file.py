from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.deezer_api import search_tracks
from handlers.song_search import build_track_buttons
from core.session import get_session, in_mode, transition, SessionMode


async def handle_music_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    music_msg = update.message
    session = get_session(context)

    if music_msg.media_group_id:
        await update.message.reply_text(
            "❌ Please send only one music file at a time."
        )
        return

    title = music_msg.audio.title if music_msg.audio and music_msg.audio.title else None
    artist = music_msg.audio.performer if music_msg.audio and music_msg.audio.performer else None
    filename = music_msg.audio.file_name if music_msg.audio and music_msg.audio.file_name else "Unknown"

    if not title:
        title = filename.rsplit(".", 1)[0] if "." in filename else filename
    if not artist:
        artist = ""

    if " - " in title:
        parts = title.split(" - ", 1)
        artist = artist or parts[0].strip()
        title = parts[1].strip()
    elif " \u2013 " in title:
        parts = title.split(" \u2013 ", 1)
        artist = artist or parts[0].strip()
        title = parts[1].strip()
    elif "_-_" in title:
        parts = title.split("_-_", 1)
        artist = artist or parts[0].strip()
        title = parts[1].strip()

    telegraph_url = session.telegraph.url
    last_data = session.telegraph.data
    has_pending_audio = session.audio.file_id is not None
    in_edit = in_mode(session, SessionMode.EDIT_FIELD) or in_mode(session, SessionMode.EDIT_LYRICS)

    if telegraph_url and last_data and not has_pending_audio and not in_edit:
        session.audio.pending_decision = {
            "file_id": music_msg.audio.file_id if music_msg.audio else None,
            "message_id": music_msg.message_id,
            "title": title,
            "artist": artist,
        }
        await transition(session, SessionMode.AUDIO_DECISION, context.bot, update.effective_chat.id)

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

    if in_edit:
        return

    session.audio.file_id = music_msg.audio.file_id if music_msg.audio else None
    session.audio.title = title
    session.audio.artist = artist
    session.audio.message_id = music_msg.message_id

    search_query = f"{artist} {title}".strip()
    results = await search_tracks(search_query)

    if results is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Search failed. Try again later."
        )
        session.audio.file_id = None
        return

    if not results:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ No results found."
        )
        session.audio.file_id = None
        return

    session.search.results = results
    session.search.page = 0
    await transition(session, SessionMode.SEARCH, context.bot, update.effective_chat.id)

    buttons = build_track_buttons(results, page=0)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🎵 Found matches for: {artist} - {title}\nSelect the track:" if artist else f"Found matches for: {title}\nSelect the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
