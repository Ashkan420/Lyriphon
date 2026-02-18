from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from handlers.song_search import song_search
from handlers.callbacks import handle_callback


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("song", song_search))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
