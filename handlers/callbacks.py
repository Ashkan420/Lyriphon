from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from services.deezer_api import get_track, get_album
from services.lrclib_api import get_lyrics
from services.telegraph_service import create_song_telegraph, edit_song_page
from telegram.constants import ParseMode
from services.url_validation import is_valid_url
import asyncio



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
                await asyncio.sleep(5)
                try:
                    await msg.delete()
                except:
                    pass
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
    edit_song_page(last_data, lyrics)

    # Reset session
    context.user_data["editing_session_active"] = False
    context.user_data["editing_field"] = None
    context.user_data["edit_prompt_id"] = None

    msg = await update.effective_chat.send_message("✅ Updated")
    await asyncio.sleep(5)
    try:
        await msg.delete()
    except:
        pass


async def cancel_edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

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

        # Clear buffers
        context.user_data["lyrics_buffer"] = []
        context.user_data["lyrics_message_ids"] = []

    # Reset session
    context.user_data["editing_session_active"] = False
    context.user_data["editing_field"] = None
    context.user_data["edit_prompt_id"] = None

    # Temporary confirmation
    msg = await update.effective_chat.send_message("❌ Edit cancelled")
    await asyncio.sleep(5)
    try:
        await msg.delete()
    except:
        pass


async def done_lyrics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("editing_session_active"):
        return

    if context.user_data.get("editing_field") != "lyrics":
        return

    # Delete /done message
    try:
        await update.message.delete()
    except:
        pass

    last_data = context.user_data.get("last_telegraph_data")
    if not last_data:
        return

    lyrics_parts = context.user_data.get("lyrics_buffer", [])
    if not lyrics_parts:
        return

    full_lyrics = "\n".join(lyrics_parts)
    context.user_data["current_lyrics"] = full_lyrics

    # Delete all lyric messages
    for msg_id in context.user_data.get("lyrics_message_ids", []):
        try:
            await context.bot.delete_message(update.effective_chat.id, msg_id)
        except:
            pass

    # Delete prompt
    prompt_id = context.user_data.get("edit_prompt_id")
    if prompt_id:
        try:
            await context.bot.delete_message(update.effective_chat.id, prompt_id)
        except:
            pass

    # Update Telegraph
    edit_song_page(last_data, full_lyrics)

    # Reset session
    context.user_data["editing_session_active"] = False
    context.user_data["editing_field"] = None
    context.user_data["edit_prompt_id"] = None
    context.user_data["lyrics_buffer"] = []
    context.user_data["lyrics_message_ids"] = []

    msg = await update.effective_chat.send_message("✅ Lyrics Updated")
    await asyncio.sleep(4)
    try:
        await msg.delete()
    except:
        pass


async def handle_cancel_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not context.user_data.get("editing_session_active"):
        await query.answer("No active edit session", show_alert=True)
        return

    await query.answer()

    # If we were editing lyrics, delete all collected lyric messages
    if context.user_data.get("editing_field") == "lyrics":
        for msg_id in context.user_data.get("lyrics_message_ids", []):
            try:
                await context.bot.delete_message(update.effective_chat.id, msg_id)
            except:
                pass

        context.user_data["lyrics_buffer"] = []
        context.user_data["lyrics_message_ids"] = []

    # Reset session
    context.user_data["editing_session_active"] = False
    context.user_data["editing_field"] = None
    context.user_data["edit_prompt_id"] = None

    await query.edit_message_text("❌ Edit cancelled")
    await asyncio.sleep(2)
    try:
        await query.message.delete()
    except:
        pass


async def handle_done_lyrics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not context.user_data.get("editing_session_active"):
        await query.answer("No active edit session", show_alert=True)
        return

    if context.user_data.get("editing_field") != "lyrics":
        await query.answer("Not in lyrics editing mode", show_alert=True)
        return

    await query.answer()

    last_data = context.user_data.get("last_telegraph_data")
    if not last_data:
        return

    lyrics_parts = context.user_data.get("lyrics_buffer", [])
    if not lyrics_parts:
        await query.answer("No lyrics to save", show_alert=True)
        return

    full_lyrics = "\n".join(lyrics_parts)
    context.user_data["current_lyrics"] = full_lyrics

    # Delete all lyric messages
    for msg_id in context.user_data.get("lyrics_message_ids", []):
        try:
            await context.bot.delete_message(update.effective_chat.id, msg_id)
        except:
            pass

    # Update Telegraph
    edit_song_page(last_data, full_lyrics)

    # Reset session
    context.user_data["editing_session_active"] = False
    context.user_data["editing_field"] = None
    context.user_data["edit_prompt_id"] = None
    context.user_data["lyrics_buffer"] = []
    context.user_data["lyrics_message_ids"] = []

    await query.edit_message_text("✅ Lyrics Updated")
    await asyncio.sleep(2)
    try:
        await query.message.delete()
    except:
        pass


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
    await asyncio.sleep(2)
    try:
        await query.message.delete()
    except:
        pass

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

    telegraph_url, telegraph_path, last_data = create_song_telegraph(
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