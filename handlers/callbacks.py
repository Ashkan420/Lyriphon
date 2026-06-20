from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from services.deezer_api import get_track, get_album, search_tracks
from services.lrclib_api import get_lyrics
from services.telegraph_service import create_song_telegraph, edit_song_page
from telegram.constants import ParseMode
from services.url_validation import is_valid_url
from handlers.escape_md import escape_md
from handlers.song_search import build_track_buttons
from handlers.telegram_utils import (
    safe_delete, delayed_delete, cancel_edit,
    search_and_show_results, attach_audio_and_prompt_channel,
)
from core.session import (
    get_session, reset_flow, in_mode, transition,
    capture_version, is_stale, SessionMode
)
import asyncio
import logging

logger = logging.getLogger(__name__)


async def finalize_lyrics(update, context, source="callback"):
    query = update.callback_query if source == "callback" else None
    session = get_session(context)

    if not in_mode(session, SessionMode.EDIT_LYRICS):
        if query:
            await query.answer("Not in lyrics editing mode", show_alert=True)
        return False

    # VERSION: detect stale async operations (capture BEFORE any mutations)
    my_version = capture_version(session)

    # LOCK: prevent double-finalization (rapid "Done" clicks)
    if session.lyrics.lock:
        if query:
            await query.answer("Already finalizing...", show_alert=True)
        return False
    session.lyrics.lock = True

    last_data = session.telegraph.data
    if not last_data:
        session.lyrics.lock = False
        if query:
            await query.answer("No song data found", show_alert=True)
        return False

    if not session.lyrics.buffer:
        session.lyrics.lock = False
        if query:
            await query.answer("No lyrics to save", show_alert=True)
        return False

    if query:
        await query.answer()

    # Capture lyrics buffer locally — don't write to session yet
    full_lyrics = "\n".join(session.lyrics.buffer)

    chat_id = update.effective_chat.id

    for msg_id in session.lyrics.message_ids:
        await safe_delete(context.bot, chat_id, msg_id)

    if session.edit.prompt_id:
        await safe_delete(context.bot, chat_id, session.edit.prompt_id)

    try:
        await asyncio.to_thread(edit_song_page, last_data, full_lyrics)
    except Exception:
        # Stale check not needed here — we're aborting anyway
        session.lyrics.lock = False
        # Transition hooks delete messages, handler owns reset
        await transition(session, SessionMode.IDLE, context.bot, chat_id)
        reset_flow(session.lyrics)
        reset_flow(session.edit)
        if query:
            await query.edit_message_text("❌ Failed to update Telegraph page")
            asyncio.create_task(safe_delete(context.bot, chat_id, query.message.message_id))
        else:
            msg = await context.bot.send_message(chat_id=chat_id, text="❌ Failed to update Telegraph page")
            asyncio.create_task(delayed_delete(context.bot, chat_id, msg.message_id, 4))
        return False

    # VERSION CHECK: stale detection AFTER async work, BEFORE committing state
    if is_stale(session, my_version):
        # Transition won't run in stale path, so release lock manually
        session.lyrics.lock = False
        return False

    # Commit state only after passing stale check
    session.telegraph.current_lyrics = full_lyrics

    # Transition hooks delete messages, handler owns reset
    await transition(session, SessionMode.IDLE, context.bot, chat_id)
    reset_flow(session.lyrics)
    reset_flow(session.edit)

    if query:
        await query.edit_message_text("✅ Lyrics Updated")
        asyncio.create_task(safe_delete(context.bot, chat_id, query.message.message_id))
    else:
        msg = await context.bot.send_message(chat_id=chat_id, text="✅ Lyrics Updated")
        asyncio.create_task(delayed_delete(context.bot, chat_id, msg.message_id, 4))

    return True


async def handle_audio_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    session = get_session(context)
    my_version = capture_version(session)

    decision = session.audio.pending_decision
    if not decision:
        try:
            await query.edit_message_text("❌ This selection has expired.")
        except:
            pass
        return

    file_id = decision.get("file_id")
    message_id = decision.get("message_id")
    title = decision.get("title", "")
    artist = decision.get("artist", "")
    chat_id = query.message.chat_id

    session.audio.pending_decision = None

    await safe_delete(context.bot, chat_id, query.message.message_id)

    if data == "audio_decision_attach":
        telegraph_url = session.telegraph.url
        last_data = session.telegraph.data
        if not telegraph_url or not last_data:
            await context.bot.send_message(chat_id=chat_id, text="❌ Telegraph expired. Send /song to create a new one.")
            return

        track_name = last_data.get("track", "Unknown Track")
        artist_name = last_data.get("artist", "Unknown Artist")

        caption = await attach_audio_and_prompt_channel(
            bot=context.bot,
            chat_id=chat_id,
            user_id=update.effective_user.id,
            session=session,
            file_id=file_id,
            telegraph_url=telegraph_url,
            track_name=track_name,
            artist_name=artist_name,
        )
        if caption is None:
            return

        session.telegraph.url = None

        if is_stale(session, my_version):
            return

        await transition(session, SessionMode.IDLE, context.bot, chat_id)

    elif data == "audio_decision_search":
        session.audio.file_id = file_id
        session.audio.title = title
        session.audio.artist = artist
        session.audio.message_id = message_id

        search_query = f"{artist} {title}".strip()
        match_text = f"{artist} - {title}" if artist else title
        ok = await search_and_show_results(
            bot=context.bot,
            chat_id=chat_id,
            session=session,
            search_query=search_query,
            display_label=match_text,
            build_track_buttons=build_track_buttons,
            search_tracks=search_tracks,
            version=my_version,
            is_stale=is_stale,
        )
        if not ok:
            session.audio.file_id = None

    elif data == "audio_decision_cancel":
        await transition(session, SessionMode.IDLE, context.bot, chat_id)
        await context.bot.send_message(chat_id=chat_id, text="❌ Cancelled.")


async def handle_edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = get_session(context)

    if in_mode(session, SessionMode.EDIT_FIELD) or in_mode(session, SessionMode.EDIT_LYRICS):
        await query.answer("❌ You already have an active edit session", show_alert=True)
        return

    await query.answer()

    field = query.data.replace("edit_field_", "")
    session.edit.field = field

    url_fields = ["track_link", "artist_link", "album_link", "cover"]

    cancel_button = [[InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")]]
    done_cancel_buttons = [
        [InlineKeyboardButton("✅ Done", callback_data="done_lyrics")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")],
    ]

    if field in url_fields:
        text = (
            f"✏️ Send new URL for: {field}\n\n"
            "• Must start with http:// or https://\n"
            "• Type 'none' to remove it"
        )
        markup = InlineKeyboardMarkup(cancel_button)
        await transition(session, SessionMode.EDIT_FIELD, context.bot, query.message.chat.id)
    else:
        if field == "lyrics":
            text = (
                "✏️ Send the new lyrics.\n\n"
                "• You can send multiple messages\n"
                "• Click Done when finished"
            )
            markup = InlineKeyboardMarkup(done_cancel_buttons)

            session.lyrics.buffer = []
            session.lyrics.message_ids = []
            await transition(session, SessionMode.EDIT_LYRICS, context.bot, query.message.chat.id)

        else:
            text = (
                f"✏️ Send new value for: {field}"
            )
            markup = InlineKeyboardMarkup(cancel_button)
            await transition(session, SessionMode.EDIT_FIELD, context.bot, query.message.chat.id)

    msg = await query.message.reply_text(text, reply_markup=markup)
    session.edit.prompt_id = msg.message_id


async def handle_new_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(context)

    if not (in_mode(session, SessionMode.EDIT_FIELD) or in_mode(session, SessionMode.EDIT_LYRICS)):
        logger.debug("Ignored message: not in edit session")
        return

    field = session.edit.field
    if not field:
        return

    if field == "lyrics":
        if session.lyrics.lock:
            return

        text = update.message.text

        if text.startswith("/"):
            return

        session.lyrics.buffer.append(text)
        session.lyrics.message_ids.append(
            update.message.message_id
        )

        prompt_id = session.edit.prompt_id
        if prompt_id:
            await safe_delete(context.bot, update.effective_chat.id, prompt_id)

        done_cancel_buttons = [
            [InlineKeyboardButton("✅ Done", callback_data="done_lyrics")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")],
        ]
        new_prompt = await update.effective_chat.send_message(
            "✏️ Send more lyrics, or click Done when finished",
            reply_markup=InlineKeyboardMarkup(done_cancel_buttons)
        )
        session.edit.prompt_id = new_prompt.message_id

        return

    new_value = update.message.text.strip()
    last_data = session.telegraph.data
    if not last_data:
        return

    await safe_delete(context.bot, update.effective_chat.id, update.message.message_id)
    prompt_id = session.edit.prompt_id
    if prompt_id:
        await safe_delete(context.bot, update.effective_chat.id, prompt_id)

    url_fields = ["track_link", "artist_link", "album_link", "cover"]

    if field in url_fields:
        if new_value.lower() == "none":
            if field == "cover":
                last_data["album_cover_url"] = ""
            else:
                last_data[field] = ""
        else:
            if not is_valid_url(new_value):
                msg = await update.effective_chat.send_message("❌ Invalid URL format")
                asyncio.create_task(delayed_delete(context.bot, update.effective_chat.id, msg.message_id, 5))
                return

            if field == "cover":
                last_data["album_cover_url"] = new_value
            else:
                last_data[field] = new_value

    else:
        if field == "track":
            last_data["track"] = new_value
        elif field == "artist":
            last_data["artist"] = new_value
        elif field == "album":
            last_data["album"] = new_value
        elif field == "date":
            last_data["release_date"] = new_value
        elif field == "author":
            last_data["author_name"] = new_value

    lyrics = session.telegraph.current_lyrics or ""
    try:
        await asyncio.to_thread(edit_song_page, last_data, lyrics)
    except Exception:
        # Transition hooks delete messages, handler owns reset
        await transition(session, SessionMode.IDLE, context.bot, update.effective_chat.id)
        reset_flow(session.edit)
        msg = await update.effective_chat.send_message("❌ Failed to update Telegraph page")
        asyncio.create_task(delayed_delete(context.bot, update.effective_chat.id, msg.message_id, 5))
        return

    # Transition hooks delete messages, handler owns reset
    await transition(session, SessionMode.IDLE, context.bot, update.effective_chat.id)
    reset_flow(session.edit)

    msg = await update.effective_chat.send_message("✅ Updated")
    asyncio.create_task(delayed_delete(context.bot, update.effective_chat.id, msg.message_id, 5))


async def cancel_edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(context)

    chat_id = update.effective_chat.id

    if in_mode(session, SessionMode.EDIT_FIELD) or in_mode(session, SessionMode.EDIT_LYRICS):
        await safe_delete(context.bot, chat_id, update.message.message_id)
        await cancel_edit(context.bot, chat_id, session)

        msg = await update.effective_chat.send_message("❌ Edit cancelled")
        asyncio.create_task(delayed_delete(context.bot, chat_id, msg.message_id, 5))
        return

    # No active edit — just clear audio state
    session.audio.clear_search_audio()
    await transition(session, SessionMode.IDLE, context.bot, chat_id)


async def done_lyrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(context)

    if not in_mode(session, SessionMode.EDIT_LYRICS):
        return

    await safe_delete(context.bot, update.effective_chat.id, update.message.message_id)
    await finalize_lyrics(update, context, source="message")


async def handle_cancel_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = get_session(context)

    if not (in_mode(session, SessionMode.EDIT_FIELD) or in_mode(session, SessionMode.EDIT_LYRICS)):
        await query.answer("No active edit session", show_alert=True)
        return

    await query.answer()

    await cancel_edit(context.bot, update.effective_chat.id, session)

    try:
        await query.edit_message_text("❌ Edit cancelled")
    except:
        pass
    asyncio.create_task(safe_delete(context.bot, update.effective_chat.id, query.message.message_id))


async def handle_done_lyrics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    session = get_session(context)

    if not in_mode(session, SessionMode.EDIT_LYRICS):
        await query.answer("No active edit session", show_alert=True)
        return

    await finalize_lyrics(update, context, source="callback")


def build_edit_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Lyrics", callback_data="edit_field_lyrics"),
            InlineKeyboardButton("👑 Author", callback_data="edit_field_author"),
        ],
        [
            InlineKeyboardButton("📝 Track", callback_data="edit_field_track"),
            InlineKeyboardButton("🔗 Track Link", callback_data="edit_field_track_link"),
        ],
        [
            InlineKeyboardButton("👤 Artist", callback_data="edit_field_artist"),
            InlineKeyboardButton("🔗 Artist Link", callback_data="edit_field_artist_link"),
        ],
        [
            InlineKeyboardButton("💽 Album", callback_data="edit_field_album"),
            InlineKeyboardButton("🔗 Album Link", callback_data="edit_field_album_link"),
        ],
        [
            InlineKeyboardButton("📅 Release Date", callback_data="edit_field_date"),
            InlineKeyboardButton("🖼 Cover URL", callback_data="edit_field_cover"),
        ],
    ])


async def send_to_channel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    session = get_session(context)

    if not data.startswith("send_channel_"):
        return

    channel_id = int(data.replace("send_channel_", ""))

    audio_file_id = session.audio.pending_file_id
    caption = session.audio.pending_caption
    telegraph_url = session.audio.pending_telegraph_url

    if not audio_file_id or not telegraph_url or not caption:
        await query.edit_message_text("❌ Nothing to send.")
        session.audio.send_channel_prompt_id = None
        return

    try:
        member = await context.bot.get_chat_member(channel_id, query.from_user.id)
        if member.status not in ["administrator", "creator"]:
            await query.answer("❌ You are not an admin in this channel.", show_alert=True)
            return
    except:
        await query.answer("❌ Can't access this channel.", show_alert=True)
        return

    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Lyrics", url=telegraph_url)]]
    )

    await context.bot.send_audio(
        chat_id=channel_id,
        audio=audio_file_id,
        caption=caption,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=button
    )

    await query.edit_message_text("✅ Sent to channel!")
    asyncio.create_task(safe_delete(context.bot, update.effective_chat.id, query.message.message_id))

    session.audio.pending_file_id = None
    session.audio.pending_caption = None
    session.audio.pending_telegraph_url = None
    session.audio.send_channel_prompt_id = None


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    session = get_session(context)
    my_version = capture_version(session)

    if not data.startswith("track_"):
        return

    track_id = int(data.replace("track_", ""))

    session.search.results = None
    session.search.page = 0

    await query.edit_message_text("⏳ Fetching track info...")

    track_data = await get_track(track_id)

    if not track_data:
        await query.edit_message_text("❌ Failed to fetch track info. Try again later.")
        return

    track_name = track_data.get("title", "Unknown Track")

    artist_data = track_data.get("artist", {})
    album_data = track_data.get("album", {})

    artist_name = artist_data.get("name", "Unknown Artist")
    artist_id = artist_data.get("id")

    album_name = album_data.get("title", "Unknown Album")
    album_id = album_data.get("id")

    album_cover_url = album_data.get("cover_xl") or album_data.get("cover_big")

    release_date = "Unknown"
    if album_id:
        await query.edit_message_text("⏳ Fetching metadata...")
        album_info = await get_album(album_id)
        if album_info:
            release_date = album_info.get("release_date", "Unknown")

    await query.edit_message_text("⏳ Fetching lyrics...")

    lyrics = await get_lyrics(track_name, artist_name)

    user = update.effective_user
    author_name = user.full_name if user else "Unknown User"

    await query.edit_message_text("⏳ Creating Telegraph page...")

    telegraph_url, telegraph_path, last_data = await asyncio.to_thread(
        create_song_telegraph,
        author_name=author_name,
        track=track_name,
        track_id=track_id,
        artist=artist_name,
        artist_id=artist_id,
        album=album_name,
        album_id=album_id,
        album_cover_url=album_cover_url,
        release_date=release_date,
        lyrics=lyrics
    )

    # VERSION CHECK: after long async work, BEFORE committing state
    if is_stale(session, my_version):
        return  # user started a new search, ignore stale result

    # Commit state only after passing stale check
    session.telegraph.current_lyrics = lyrics
    session.telegraph.url = telegraph_url
    session.telegraph.path = telegraph_path
    session.telegraph.data = last_data

    pending_audio_file_id = session.audio.file_id
    has_audio = bool(pending_audio_file_id)

    if has_audio:
        pending_message_id = session.audio.message_id

        caption = await attach_audio_and_prompt_channel(
            bot=context.bot,
            chat_id=query.message.chat_id,
            user_id=update.effective_user.id,
            session=session,
            file_id=pending_audio_file_id,
            telegraph_url=telegraph_url,
            track_name=track_name,
            artist_name=artist_name,
        )
        if caption is None:
            await query.edit_message_text("❌ Failed to attach audio. Try again.")
            session.audio.file_id = None
            return

        if pending_message_id:
            await safe_delete(context.bot, query.message.chat_id, pending_message_id)

        session.audio.clear_search_audio()
        session.telegraph.url = None

    status = "Telegraph Created & Audio Attached" if has_audio else "Telegraph Created"
    extra = "" if has_audio else "Send a music file to attach the Lyrics button to it.\n\n"

    is_inline = bool(query.inline_message_id)
    if is_inline:
        await query.edit_message_text(
            f"<a href=\"{telegraph_url}\">{track_name} - {artist_name}</a>",
            parse_mode="HTML"
        )
    else:
        reply_markup = build_edit_menu()
        await query.edit_message_text(
            f"✅ <b>{status}</b>\n\n"
            f"<blockquote>"
            f"🎵 <b>{track_name}</b>\n"
            f"👤 {artist_name}\n"
            f"💽 {album_name}\n"
            f"📅 {release_date}"
            f"</blockquote>\n\n"
            f"{extra}"
            f"👇 Edit options below — or tap to open the page:\n"
            f'<a href="{telegraph_url}">📖 Open Telegraph Page</a>',
            parse_mode="HTML",
            reply_markup=reply_markup
        )
