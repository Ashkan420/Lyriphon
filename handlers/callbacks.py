from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from services.deezer_api import get_track, get_album, search_tracks
from services.lrclib_api import get_lyrics
from services.telegraph_service import create_song_telegraph, edit_song_page
from telegram.constants import ParseMode
from services.url_validation import is_valid_url
from handlers.escape_md import escape_md
from handlers.song_search import build_track_buttons
import asyncio
import logging

logger = logging.getLogger(__name__)


async def _delayed_delete(bot, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass


async def _safe_delete(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass


def reset_edit_session(context):
    context.user_data["editing_session_active"] = False
    context.user_data["editing_field"] = None
    context.user_data["edit_prompt_id"] = None
    context.user_data["lyrics_buffer"] = []
    context.user_data["lyrics_message_ids"] = []


async def finalize_lyrics(update, context, source="callback"):
    query = update.callback_query if source == "callback" else None

    if context.user_data.get("editing_field") != "lyrics":
        if query:
            await query.answer("Not in lyrics editing mode", show_alert=True)
        return False

    last_data = context.user_data.get("last_telegraph_data")
    if not last_data:
        if query:
            await query.answer("No song data found", show_alert=True)
        return False

    lyrics_parts = context.user_data.get("lyrics_buffer", [])
    if not lyrics_parts:
        if query:
            await query.answer("No lyrics to save", show_alert=True)
        return False

    if context.user_data.get("lyrics_finalizing"):
        if query:
            await query.answer("Already finalizing...", show_alert=True)
        return False

    context.user_data["lyrics_finalizing"] = True

    if query:
        await query.answer()

    full_lyrics = "\n".join(lyrics_parts)
    context.user_data["current_lyrics"] = full_lyrics

    chat_id = update.effective_chat.id

    for msg_id in context.user_data.get("lyrics_message_ids", []):
        try:
            await context.bot.delete_message(chat_id, msg_id)
        except:
            pass

    prompt_id = context.user_data.get("edit_prompt_id")
    if prompt_id:
        try:
            await context.bot.delete_message(chat_id, prompt_id)
        except:
            pass

    try:
        await asyncio.to_thread(edit_song_page, last_data, full_lyrics)
    except Exception:
        reset_edit_session(context)
        context.user_data["lyrics_finalizing"] = False
        if query:
            await query.edit_message_text("❌ Failed to update Telegraph page")
            asyncio.create_task(_safe_delete(context.bot, chat_id, query.message.message_id))
        else:
            msg = await context.bot.send_message(chat_id=chat_id, text="❌ Failed to update Telegraph page")
            asyncio.create_task(_delayed_delete(context.bot, chat_id, msg.message_id, 4))
        return False

    reset_edit_session(context)
    context.user_data["lyrics_finalizing"] = False

    if query:
        await query.edit_message_text("✅ Lyrics Updated")
        asyncio.create_task(_safe_delete(context.bot, chat_id, query.message.message_id))
    else:
        msg = await context.bot.send_message(chat_id=chat_id, text="✅ Lyrics Updated")
        asyncio.create_task(_delayed_delete(context.bot, chat_id, msg.message_id, 4))

    return True


async def handle_audio_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    decision = context.user_data.get("pending_audio_decision")
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

    context.user_data["pending_audio_decision"] = None

    try:
        await context.bot.delete_message(chat_id, query.message.message_id)
    except:
        pass

    if data == "audio_decision_attach":
        telegraph_url = context.user_data.get("last_telegraph")
        last_data = context.user_data.get("last_telegraph_data")
        if not telegraph_url or not last_data:
            await context.bot.send_message(chat_id=chat_id, text="❌ Telegraph expired. Send /song to create a new one.")
            return

        track_name = last_data.get("track", "Unknown Track")
        artist_name = last_data.get("artist", "Unknown Artist")

        track_name_md = escape_md(track_name)
        artist_name_md = escape_md(artist_name)

        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Lyrics", url=telegraph_url)]]
        )
        hidden_link = f"[‎]({telegraph_url})"
        caption = f'>`{track_name_md} — {artist_name_md}`{hidden_link}'

        try:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=button,
            )
        except Exception:
            await context.bot.send_message(chat_id=chat_id, text="❌ Failed to attach audio.")
            return

        if file_id:
            context.user_data["pending_audio_file_id"] = file_id
            context.user_data["pending_caption"] = caption
            context.user_data["pending_telegraph_url"] = telegraph_url

        from db import get_user_channels
        user_channels = await get_user_channels(update.effective_user.id)
        if user_channels:
            channel_buttons = [
                [InlineKeyboardButton(ch_title, callback_data=f"send_channel_{cid}")]
                for cid, ch_title in user_channels.items()
            ]
            prompt = await context.bot.send_message(
                chat_id=chat_id,
                text="Send to which channel?",
                reply_markup=InlineKeyboardMarkup(channel_buttons)
            )
            context.user_data["send_channel_prompt_id"] = prompt.message_id

        context.user_data["last_telegraph"] = None

    elif data == "audio_decision_search":
        context.user_data["pending_audio"] = {
            "file_id": file_id,
            "title": title,
            "artist": artist,
            "mode": "auto_audio_flow",
            "message_id": message_id,
        }

        search_query = f"{artist} {title}".strip()
        results = await search_tracks(search_query)

        if results is None:
            await context.bot.send_message(chat_id=chat_id, text="❌ Search failed. Try again later.")
            context.user_data["pending_audio"] = None
            return

        if not results:
            await context.bot.send_message(chat_id=chat_id, text="❌ No results found.")
            context.user_data["pending_audio"] = None
            return

        context.user_data["song_search_results"] = results
        context.user_data["song_search_page"] = 0

        buttons = build_track_buttons(results, page=0)
        match_text = f"{artist} - {title}" if artist else title
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎵 Found matches for: {match_text}\nSelect the track:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data == "audio_decision_cancel":
        await context.bot.send_message(chat_id=chat_id, text="❌ Cancelled.")


async def handle_edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Per-user session lock
    if context.user_data.get("editing_session_active"):
        await query.answer("❌ You already have an active edit session", show_alert=True)
        return
    context.user_data["editing_session_active"] = True

    await query.answer()  # answer immediately to remove "loading..." popup

    field = query.data.replace("edit_field_", "")
    context.user_data["editing_field"] = field

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
    else:
        if field == "lyrics":
            text = (
                "✏️ Send the new lyrics.\n\n"
                "• You can send multiple messages\n"
                "• Click Done when finished"
            )
            markup = InlineKeyboardMarkup(done_cancel_buttons)

            # Prepare buffer
            context.user_data["lyrics_buffer"] = []
            context.user_data["lyrics_message_ids"] = []

        else:
            text = (
                f"✏️ Send new value for: {field}"
            )
            markup = InlineKeyboardMarkup(cancel_button)


    msg = await query.message.reply_text(text, reply_markup=markup)
    context.user_data["edit_prompt_id"] = msg.message_id




async def handle_new_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Must be in active edit session
    if not context.user_data.get("editing_session_active"):
        logger.debug("Ignored message: not in edit session")
        return

    field = context.user_data.get("editing_field")
    if not field:
        return

    # LYRICS COLLECTION MODE
    if field == "lyrics":

        text = update.message.text

        # Ignore commands except /done (handled elsewhere)
        if text.startswith("/"):
            return

        context.user_data.setdefault("lyrics_buffer", []).append(text)
        context.user_data.setdefault("lyrics_message_ids", []).append(
            update.message.message_id
        )

        # Delete old prompt and send new one
        prompt_id = context.user_data.get("edit_prompt_id")
        if prompt_id:
            try:
                await context.bot.delete_message(update.effective_chat.id, prompt_id)
            except:
                pass

        done_cancel_buttons = [
            [InlineKeyboardButton("✅ Done", callback_data="done_lyrics")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_edit")],
        ]
        new_prompt = await update.effective_chat.send_message(
            "✏️ Send more lyrics, or click Done when finished",
            reply_markup=InlineKeyboardMarkup(done_cancel_buttons)
        )
        context.user_data["edit_prompt_id"] = new_prompt.message_id

        return


    new_value = update.message.text.strip()
    last_data = context.user_data.get("last_telegraph_data")
    if not last_data:
        return

    # Delete user's message and prompt
    try:
        await update.message.delete()
    except:
        pass
    prompt_id = context.user_data.get("edit_prompt_id")
    if prompt_id:
        try:
            await context.bot.delete_message(update.effective_chat.id, prompt_id)
        except:
            pass

    url_fields = ["track_link", "artist_link", "album_link", "cover"]

    # Handle URL fields
    if field in url_fields:
        if new_value.lower() == "none":
            if field == "cover":
                last_data["album_cover_url"] = ""
            else:
                last_data[field] = ""
        else:
            if not is_valid_url(new_value):
                msg = await update.effective_chat.send_message("❌ Invalid URL format")
                asyncio.create_task(_delayed_delete(context.bot, update.effective_chat.id, msg.message_id, 5))
                return

            if field == "cover":
                last_data["album_cover_url"] = new_value
            else:
                last_data[field] = new_value


    # Handle non-URL fields
    else:
        if field == "lyrics":
            context.user_data["current_lyrics"] = new_value
        elif field == "track":
            last_data["track"] = new_value
        elif field == "artist":
            last_data["artist"] = new_value
        elif field == "album":
            last_data["album"] = new_value
        elif field == "date":
            last_data["release_date"] = new_value
        elif field == "author":
            last_data["author_name"] = new_value

    # Rebuild Telegraph page
    lyrics = context.user_data.get("current_lyrics", "")
    try:
        await asyncio.to_thread(edit_song_page, last_data, lyrics)
    except Exception:
        reset_edit_session(context)
        msg = await update.effective_chat.send_message("❌ Failed to update Telegraph page")
        asyncio.create_task(_delayed_delete(context.bot, update.effective_chat.id, msg.message_id, 5))
        return

    reset_edit_session(context)

    msg = await update.effective_chat.send_message("✅ Updated")
    asyncio.create_task(_delayed_delete(context.bot, update.effective_chat.id, msg.message_id, 5))


async def cancel_edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # Clear pending audio session if active
    if context.user_data.get("pending_audio"):
        context.user_data["pending_audio"] = None

    if not context.user_data.get("editing_session_active"):
        return

    # Delete /cancel message
    try:
        await update.message.delete()
    except:
        pass

    # Delete prompt
    prompt_id = context.user_data.get("edit_prompt_id")
    if prompt_id:
        try:
            await context.bot.delete_message(update.effective_chat.id, prompt_id)
        except:
            pass

    # If we were editing lyrics → delete all collected lyric messages
    if context.user_data.get("editing_field") == "lyrics":
        for msg_id in context.user_data.get("lyrics_message_ids", []):
            try:
                await context.bot.delete_message(update.effective_chat.id, msg_id)
            except:
                pass

    reset_edit_session(context)

    # Temporary confirmation
    msg = await update.effective_chat.send_message("❌ Edit cancelled")
    asyncio.create_task(_delayed_delete(context.bot, update.effective_chat.id, msg.message_id, 5))


async def done_lyrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("editing_session_active"):
        return

    # Delete /done message
    try:
        await update.message.delete()
    except:
        pass

    await finalize_lyrics(update, context, source="message")


async def handle_cancel_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not context.user_data.get("editing_session_active"):
        await query.answer("No active edit session", show_alert=True)
        return

    await query.answer()

    if context.user_data.get("editing_field") == "lyrics":
        for msg_id in context.user_data.get("lyrics_message_ids", []):
            try:
                await context.bot.delete_message(update.effective_chat.id, msg_id)
            except:
                pass

    reset_edit_session(context)

    try:
        await query.edit_message_text("❌ Edit cancelled")
    except:
        pass
    asyncio.create_task(_safe_delete(context.bot, update.effective_chat.id, query.message.message_id))


async def handle_done_lyrics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not context.user_data.get("editing_session_active"):
        await query.answer("No active edit session", show_alert=True)
        return

    await finalize_lyrics(update, context, source="callback")


# Build buttons
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

    if not data.startswith("send_channel_"):
        return

    channel_id = int(data.replace("send_channel_", ""))

    audio_file_id = context.user_data.get("pending_audio_file_id")
    caption = context.user_data.get("pending_caption")
    telegraph_url = context.user_data.get("pending_telegraph_url")

    if not audio_file_id or not telegraph_url or not caption:
        await query.edit_message_text("❌ Nothing to send.")
        context.user_data["send_channel_prompt_id"] = None
        return

    # check if user is admin in that channel
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
    asyncio.create_task(_safe_delete(context.bot, update.effective_chat.id, query.message.message_id))

    # cleanup
    context.user_data["pending_audio_file_id"] = None
    context.user_data["pending_caption"] = None
    context.user_data["pending_telegraph_url"] = None
    context.user_data["send_channel_prompt_id"] = None



async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if not data.startswith("track_"):
        return

    track_id = int(data.replace("track_", ""))

    # Clear stale search results
    context.user_data["song_search_results"] = None
    context.user_data["song_search_page"] = None

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

    # Get release date from album endpoint
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
    author_url = "https://t.me/bichniga"

    #if user and user.username:
    #    author_url = f"https://t.me/{user.username}"

    await query.edit_message_text("⏳ Creating Telegraph page...")

    telegraph_url, telegraph_path, last_data = await asyncio.to_thread(
        create_song_telegraph,
        author_name=author_name,
        #author_url=author_url,
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

    # store it for this user
    context.user_data["current_lyrics"] = lyrics
    context.user_data["last_telegraph"] = telegraph_url
    context.user_data["last_telegraph_path"] = telegraph_path
    context.user_data["last_track_name"] = track_name
    context.user_data["last_artist_name"] = artist_name
    context.user_data["last_telegraph_data"] = last_data

    # Check if there's a pending audio to auto-attach
    pending_audio = context.user_data.get("pending_audio")
    if pending_audio and pending_audio.get("file_id"):
        # Auto-attach the audio
        file_id = pending_audio["file_id"]
        message_id = pending_audio.get("message_id")

        # Create caption with telegraph link
        track_name_md = escape_md(track_name)
        artist_name_md = escape_md(artist_name)
        hidden_link = f"[‎]({telegraph_url})"
        caption = f'>`{track_name_md} — {artist_name_md}`{hidden_link}'

        # Send audio with telegraph button
        button = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Lyrics", url=telegraph_url)]]
        )

        try:
            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=button
            )
        except Exception:
            await query.edit_message_text("❌ Failed to attach audio. Try again.")
            context.user_data["pending_audio"] = None
            return

        # Store for channel sending
        context.user_data["pending_audio_file_id"] = file_id
        context.user_data["pending_caption"] = caption
        context.user_data["pending_telegraph_url"] = telegraph_url

        # Delete the original audio message
        if message_id:
            try:
                await context.bot.delete_message(
                    chat_id=query.message.chat_id,
                    message_id=message_id
                )
            except:
                pass

        # Clear pending audio and telegraph state
        context.user_data["pending_audio"] = None
        context.user_data["last_telegraph"] = None

        # Ask which channel to send to
        from db import get_user_channels
        user_channels = await get_user_channels(update.effective_user.id)
        if user_channels:
            channel_buttons = [
                [InlineKeyboardButton(title, callback_data=f"send_channel_{chat_id}")]
                for chat_id, title in user_channels.items()
            ]
            prompt = await query.message.reply_text(
                "Send to which channel?",
                reply_markup=InlineKeyboardMarkup(channel_buttons)
            )
            context.user_data["send_channel_prompt_id"] = prompt.message_id

        # Edit the search message to show success
        is_inline = bool(query.inline_message_id)
        if is_inline:
            await query.edit_message_text(
                f"<a href=\"{telegraph_url}\">{track_name} - {artist_name}</a>",
                parse_mode="HTML"
            )
        else:
            reply_markup = build_edit_menu()
            await query.edit_message_text(
                f"✅ <b>Telegraph Created & Audio Attached</b>\n\n"
                f"<blockquote>"
                f"🎵 <b>{track_name}</b>\n"
                f"👤 {artist_name}\n"
                f"💽 {album_name}\n"
                f"📅 {release_date}"
                f"</blockquote>\n\n"
                f"👇 Edit options below — or tap to open the page:\n"
                f'<a href="{telegraph_url}">📖 Open Telegraph Page</a>',
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        return

    # No pending audio - show normal message
    is_inline = bool(query.inline_message_id)
    if is_inline:
        await query.edit_message_text(
            f"<a href=\"{telegraph_url}\">{track_name} - {artist_name}</a>",
            parse_mode="HTML"
        )
    else:
        reply_markup = build_edit_menu()

        await query.edit_message_text(
            f"✅ <b>Telegraph Created</b>\n\n"
            f"<blockquote>"
            f"🎵 <b>{track_name}</b>\n"
            f"👤 {artist_name}\n"
            f"💽 {album_name}\n"
            f"📅 {release_date}"
            f"</blockquote>\n\n"
            f"Send a music file to attach the Lyrics button to it.\n\n"
            f"👇 Edit options below — or tap to open the page:\n"
            f'<a href="{telegraph_url}">📖 Open Telegraph Page</a>',
            parse_mode="HTML",
            reply_markup=reply_markup
        )