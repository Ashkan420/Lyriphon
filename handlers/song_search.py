from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.deezer_api import search_tracks

PAGE_SIZE = 5  # tracks per page


def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


def build_track_buttons(results, page: int = 0):
    """
    Build inline keyboard for a page of results with Next/Previous/First navigation.
    """
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

    # Navigation row
    nav_buttons = []

    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"search_page_{page-1}"))

    if len(results) > end:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"search_page_{page+1}"))

    # First page button only on the last page
    total_pages = (len(results) - 1) // PAGE_SIZE
    if page == total_pages and total_pages > 0:
        nav_buttons.insert(0, InlineKeyboardButton("⏪ First", callback_data="search_page_0"))

    if nav_buttons:
        buttons.append(nav_buttons)

    return buttons


async def song_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /song command with paginated results."""
    prompt_id = context.user_data.get("send_channel_prompt_id")
    if prompt_id:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=prompt_id)
        except:
            pass
        context.user_data["send_channel_prompt_id"] = None

    if not context.args:
        await update.message.reply_text("❌ Usage: /song <track name>")
        return

    query = " ".join(context.args)
    results = search_tracks(query)

    if not results:
        await update.message.reply_text("❌ No results found.")
        return

    context.user_data["song_search_results"] = results
    context.user_data["song_search_page"] = 0

    buttons = build_track_buttons(results, page=0)

    await update.message.reply_text(
        text="🎵 Select the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def handle_search_page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Next / Previous / First button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data.startswith("search_page_"):
        return

    page = int(data.replace("search_page_", ""))
    results = context.user_data.get("song_search_results", [])

    if not results:
        await query.edit_message_text("❌ Search expired. Try again with /song.")
        return

    context.user_data["song_search_page"] = page
    buttons = build_track_buttons(results, page=page)

    await query.edit_message_text(
        text="🎵 Select the track:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
