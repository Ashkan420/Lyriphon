from telegram import Update
from telegram.ext import ContextTypes
from services.deezer_api import get_track, get_album
from services.lrclib_api import get_lyrics
from services.telegraph_service import create_song_telegraph


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
    author_url = ""

    if user and user.username:
        author_url = f"https://t.me/{user.username}"

    await query.edit_message_text("⏳ Creating Telegraph page...")

    telegraph_url = create_song_telegraph(
        author_name=author_name,
        author_url=author_url,
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

    await query.edit_message_text(
        f"✅ Telegraph created!\n\n🔗 {telegraph_url}"
    )
