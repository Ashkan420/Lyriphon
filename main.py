from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.song_search import song_search
from handlers.callbacks import handle_callback
from handlers.handle_music_file import handle_music_file


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("song", song_search))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.AUDIO, handle_music_file))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
