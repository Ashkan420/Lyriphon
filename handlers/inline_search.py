from telegram import Update, InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from services.deezer_api import search_tracks
from utils.telegram import format_duration


async def inline_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    query_text = query.query.strip()

    if not query_text:
        await query.answer(
            [],
            cache_time=300,
            is_personal=True,
            switch_pm_text="Type a song name to search",
            switch_pm_parameter="help"
        )
        return

    results = await search_tracks(query_text, limit=5)

    if not results:
        await query.answer([], cache_time=60, is_personal=True)
        return

    articles = []
    for item in results:
        track_name = item.get("title", "Unknown")
        artist_name = item.get("artist", {}).get("name", "Unknown")
        track_id = item.get("id")
        duration = item.get("duration", 0)
        album_cover = item.get("album", {}).get("cover_medium", "")

        dur_text = format_duration(duration)

        message_text = (
            f"🎵 *{track_name}*\n"
            f"👤 {artist_name}\n"
            f"⏱ {dur_text}"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 Get Lyrics", callback_data=f"track_{track_id}")]
        ])

        article = InlineQueryResultArticle(
            id=str(track_id),
            title=f"{track_name} - {artist_name}",
            description=f"{artist_name} ({dur_text})",
            thumbnail_url=album_cover if album_cover else None,
            input_message_content=InputTextMessageContent(
                message_text=message_text,
                parse_mode=ParseMode.MARKDOWN,
            ),
            reply_markup=keyboard,
        )
        articles.append(article)

    await query.answer(articles, cache_time=300, is_personal=True)
