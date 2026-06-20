import asyncio

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from utils.escape_md import escape_md
from core.session import get_session, reset_flow, transition, SessionMode
from db import get_user_channels


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

async def safe_delete(bot, chat_id, message_id):
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def delayed_delete(bot, chat_id, message_id, delay):
    await asyncio.sleep(delay)
    await safe_delete(bot, chat_id, message_id)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def format_duration(seconds: int) -> str:
    minutes = seconds // 60
    sec = seconds % 60
    return f"{minutes}:{sec:02d}"


# ---------------------------------------------------------------------------
# Search → display results
# ---------------------------------------------------------------------------

async def search_and_show_results(
    bot,
    chat_id,
    session,
    search_query,
    display_label,
    build_track_buttons,
    search_tracks,
    version=None,
    is_stale=None,
):
    """Run a Deezer search, guard for staleness, set session state, and
    send the track-selection message.  Returns True on success."""
    results = await search_tracks(search_query)

    if results is None:
        await bot.send_message(chat_id=chat_id, text="❌ Search failed. Try again later.")
        return False

    if not results:
        await bot.send_message(chat_id=chat_id, text="❌ No results found.")
        return False

    if version is not None and is_stale is not None and is_stale(session, version):
        return False

    session.search.results = results
    session.search.page = 0
    await transition(session, SessionMode.SEARCH, bot, chat_id)

    buttons = build_track_buttons(results, page=0)
    text = f"🎵 Found matches for: {display_label}\nSelect the track:" if display_label else "🎵 Select the track:"
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return True


# ---------------------------------------------------------------------------
# Audio attach → channel prompt
# ---------------------------------------------------------------------------

async def attach_audio_and_prompt_channel(
    bot,
    chat_id,
    user_id,
    session,
    file_id,
    telegraph_url,
    track_name,
    artist_name,
):
    """Build caption, send audio with Lyrics button, and show the
    send-to-channel prompt if the user has channels.  Returns the caption
    string on success, or None on failure."""
    track_name_md = escape_md(track_name)
    artist_name_md = escape_md(artist_name)
    hidden_link = f"[‎]({telegraph_url})"
    caption = f'>`{track_name_md} — {artist_name_md}`{hidden_link}'

    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Lyrics", url=telegraph_url)]]
    )

    try:
        await bot.send_audio(
            chat_id=chat_id,
            audio=file_id,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=button,
        )
    except Exception:
        await bot.send_message(chat_id=chat_id, text="❌ Failed to attach audio.")
        return None

    session.audio.pending_file_id = file_id
    session.audio.pending_caption = caption
    session.audio.pending_telegraph_url = telegraph_url

    user_channels = await get_user_channels(user_id)
    if user_channels:
        channel_buttons = [
            [InlineKeyboardButton(title, callback_data=f"send_channel_{cid}")]
            for cid, title in user_channels.items()
        ]
        prompt = await bot.send_message(
            chat_id=chat_id,
            text="Send to which channel?",
            reply_markup=InlineKeyboardMarkup(channel_buttons),
        )
        session.audio.send_channel_prompt_id = prompt.message_id

    return caption


# ---------------------------------------------------------------------------
# Cancel-edit helper
# ---------------------------------------------------------------------------

async def cancel_edit(bot, chat_id, session):
    """Transition to IDLE and reset edit/lyrics flows."""
    await transition(session, SessionMode.IDLE, bot, chat_id)
    reset_flow(session.edit)
    reset_flow(session.lyrics)
