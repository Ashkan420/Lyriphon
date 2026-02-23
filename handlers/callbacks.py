from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from services.deezer_api import get_track, get_album
from services.lrclib_api import get_lyrics
from services.telegraph_service import create_song_telegraph, edit_song_page
from telegram.constants import ParseMode
from url_validation import is_valid_url

async def handle_edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    field = query.data.replace("edit_field_", "")
    context.user_data["editing_field"] = field

    url_fields = ["track_link", "artist_link", "album_link", "cover"]

    if field in url_fields:
        text = (
            f"✏️ Send new URL for: {field}\n\n"
            "• Must start with http:// or https://\n"
            "• Type 'none' to remove it\n"
            "• Send /cancel to stop editing"
        )
    else:
        text = (
            f"✏️ Send new value for: {field}\n\n"
            "Send /cancel to stop editing."
        )

    msg = await query.message.reply_text(text)
    context.user_data["edit_prompt_id"] = msg.message_id
    

async def handle_new_field_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.startswith("/"):
        return

    field = context.user_data.get("editing_field")
    if not field:
        return

    new_value = update.message.text
    last_data = context.user_data.get("last_telegraph_data")

    if not last_data:
        await update.message.reply_text("❌ No Telegraph page loaded.")
        return

    # Update data
    if field == "lyrics":
        context.user_data["current_lyrics"] = new_value

    elif field == "track":
        last_data["track"] = new_value  # also updates title automatically

    elif field == "track_link":
        last_data["track_link"] = new_value

    elif field == "artist":
        last_data["artist"] = new_value

    elif field == "artist_link":
        last_data["artist_link"] = new_value

    elif field == "album":
        last_data["album"] = new_value

    elif field == "album_link":
        last_data["album_link"] = new_value

    elif field == "cover":
        last_data["album_cover_url"] = new_value

    elif field == "date":
        last_data["release_date"] = new_value

    elif field == "author":
        last_data["author_name"] = new_value


    # Clean chat
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

    # Rebuild page
    lyrics = context.user_data.get("current_lyrics", "")
    edit_song_page(last_data, lyrics)

    # Reset editing state
    context.user_data["editing_field"] = None

    await update.effective_chat.send_message(
        "✅ Updated successfully!",
    )




async def cancel_edit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("editing_field"):
        return

    # Delete the user's /cancel message
    try:
        await update.message.delete()
    except:
        pass

    # Delete the prompt message that asked for input
    prompt_id = context.user_data.get("edit_prompt_id")
    if prompt_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=prompt_id
            )
        except:
            pass

    # Reset editing state
    context.user_data["editing_field"] = None
    context.user_data["edit_prompt_id"] = None

    # Send clean confirmation + show menu again
    await update.effective_chat.send_message(
        "❌ Edit cancelled.",
    )



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

    context.user_data["send_channel_prompt_id"] = None

    await query.delete_message()

    print("CALLBACK DATA:", query.data)
    print("CHANNEL ID:", channel_id)

    # cleanup
    context.user_data["pending_audio_file_id"] = None
    context.user_data["pending_caption"] = None
    context.user_data["pending_telegraph_url"] = None
    context.user_data["send_channel_prompt_id"] = None


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
            InlineKeyboardButton("🖼 Cover URL", callback_data="edit_field_cover"),
            InlineKeyboardButton("📅 Release Date", callback_data="edit_field_date"),
        ],
    ])




async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if not data.startswith("track_"):
        return

    track_id = int(data.replace("track_", ""))

    await query.edit_message_text("⏳ Fetching track info...")

    track_data = get_track(track_id)

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
        album_info = get_album(album_id)
        release_date = album_info.get("release_date", "Unknown")

    await query.edit_message_text("⏳ Fetching lyrics...")

    lyrics = get_lyrics(track_name, artist_name)

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
        f"✅ Telegraph created\n\n"
        "You can now send a music file in this chat to attach the 'Lyrics' button to it.\n"
        "After attaching, you'll also have the option to send it to channels you added the bot to.\n\n"
        f'<a href="{telegraph_url}">Open Telegraph Page</a>',
        parse_mode="HTML",
        reply_markup=reply_markup
    )