from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.deezer_api import search_tracks
from core.session import get_session, in_mode, transition, SessionMode

PAGE_SIZE = 5


def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


def build_track_buttons(results, page: int = 0):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_results = results[start:end]

    buttons = []
    for item in page_results:
        track_name = item.get("title", "Unknown")
        artist_name = item.get("artist", {}).get("name", "Unknown")
        duration = item.get("duration", 0)
        track_id = item.get("id")
        dur_text = format_duration(duration)

        button_text = f"{track_name} - {artist_name} ({dur_text})"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"track_{track_id}")])

    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search_page_{page-1}"))

    if len(results) > end:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_page_{page+1}"))

    total_pages = (len(results) - 1) // PAGE_SIZE
    if page == total_pages and total_pages > 0:
        nav_buttons.insert(0, InlineKeyboardButton("⏪ First", callback_data="search_page_0"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return buttons


async def song_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(context)

    # Clear search audio
    session.audio.file_id = None
    session.audio.title = None
    session.audio.artist = None
    session.audio.message_id = None

    # Clear pending channel prompt
    if session.audio.send_channel_prompt_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=session.audio.send_channel_prompt_id
            )
        except:
            pass
        session.audio.send_channel_prompt_id = None

    if not context.args:
        await update.message.reply_text("❌ Usage: /song <track name>")
        return

    query = " ".join(context.args)
    results = await search_tracks(query)

    if results is None:
        await update.message.reply_text("❌ Search failed. Try again later.")
        return

    if not results:
        await update.message.reply_text("❌ No results found.")
        return

    session.search.results = results
    session.search.page = 0
    await transition(session, SessionMode.SEARCH, context.bot, update.effective_chat.id)

    buttons = build_track_buttons(results, page=0)

    await update.message.reply_text(
        text="🎵 Select the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    session = get_session(context)

    if not data.startswith("search_page_"):
        return

    page = int(data.replace("search_page_", ""))
    results = session.search.results

    if not results:
        await query.edit_message_text("❌ Search expired. Try again with /song.")
        return

    session.search.page = page
    buttons = build_track_buttons(results, page=page)

    await query.edit_message_text(
        text="🎵 Select the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
