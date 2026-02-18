from multiprocessing import context
from turtle import update
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.deezer_api import search_tracks


def format_duration(seconds: int):
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


async def song_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /song <track name>")
        return

    query = " ".join(context.args)

    await update.message.reply_text("🔍 Searching Deezer...")

    results = search_tracks(query)

    if not results:
        await update.message.reply_text("❌ No results found.")
        return

    buttons = []
    for item in results:
        track_name = item.get("title", "Unknown")
        artist_name = item.get("artist", {}).get("name", "Unknown")
        duration = item.get("duration", 0)
        track_id = item.get("id")

        dur_text = format_duration(duration)

        button_text = f"{track_name} - {artist_name} ({dur_text})"

        buttons.append([
            InlineKeyboardButton(button_text, callback_data=f"track_{track_id}")
        ])

    await update.message.reply_text(
        "🎵 Select the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )



