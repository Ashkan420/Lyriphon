"""Bot entry point — builds the Application, registers all handlers, and starts polling."""

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, InlineQueryHandler, filters, ChatMemberHandler
from config import BOT_TOKEN
from handlers.start import start_command, help_command
from handlers.song_search import song_search, handle_search_page_callback
from handlers.callbacks import handle_callback, send_to_channel_callback, handle_edit_field_callback, handle_new_field_value, cancel_edit_command, done_lyrics_command, handle_cancel_edit_callback, handle_done_lyrics_callback, handle_audio_decision_callback
from handlers.music_file import handle_music_file
from handlers.channel_tracker import track_channels
from handlers.inline_search import inline_search
from core.session import session_debug_command
from db import init_db


async def post_init(app):
    """Initialize the database pool after the Application is built."""
    await init_db()

app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

# --- Command handlers ---
app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("song", song_search))
app.add_handler(CommandHandler("done", done_lyrics_command))
app.add_handler(CommandHandler("cancel", cancel_edit_command))
app.add_handler(CommandHandler("session", session_debug_command))

# --- Chat member tracking ---
app.add_handler(ChatMemberHandler(track_channels, ChatMemberHandler.MY_CHAT_MEMBER))

# --- Callback query handlers (pattern-matched) ---
app.add_handler(CallbackQueryHandler(handle_audio_decision_callback, pattern="^audio_decision_"))
app.add_handler(CallbackQueryHandler(handle_search_page_callback, pattern="^search_page_"))
app.add_handler(CallbackQueryHandler(handle_callback, pattern="^track_"))
app.add_handler(CallbackQueryHandler(handle_edit_field_callback, pattern="^edit_field_"))
app.add_handler(CallbackQueryHandler(send_to_channel_callback, pattern="^send_channel_"))
app.add_handler(CallbackQueryHandler(handle_cancel_edit_callback, pattern="^cancel_edit$"))
app.add_handler(CallbackQueryHandler(handle_done_lyrics_callback, pattern="^done_lyrics$"))

# --- Inline and free-text handlers ---
app.add_handler(InlineQueryHandler(inline_search))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_field_value))
app.add_handler(MessageHandler(filters.AUDIO, handle_music_file))


if __name__ == "__main__":
    print("Bot running...")
    app.run_polling()
