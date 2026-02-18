from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from services.deezer_api import get_track, get_album
from services.lrclib_api import get_lyrics
from services.telegraph_service import create_song_telegraph
from telegram.constants import ParseMode


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
        await query.edit_message_text("⏳ Fetching album release date...")
        album_info = get_album(album_id)
        release_date = album_info.get("release_date", "Unknown")

    await query.edit_message_text("⏳ Fetching lyrics from LRCLIB...")

    lyrics = get_lyrics(track_name, artist_name)

    user = update.effective_user
    author_name = user.full_name if user else "Unknown User"
    author_url = "https://t.me/bichniga"

    #if user and user.username:
    #    author_url = f"https://t.me/{user.username}"

    await query.edit_message_text("⏳ Creating Telegraph page...")

    telegraph_url = create_song_telegraph(
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
    context.user_data["last_telegraph"] = telegraph_url
    context.user_data["last_track_name"] = track_name
    context.user_data["last_artist_name"] = artist_name

    # Send a message with an inline button linking to the Telegraph page
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Click for Lyrics 🎵", url=telegraph_url)]]
    )

    await query.edit_message_text(
        "✅ Telegraph created! Click the button below to open it:",
        reply_markup=button
    )
