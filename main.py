from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.song_search import song_search
from handlers.callbacks import handle_callback
from handlers.handle_music_file import handle_music_file
from handlers.callbacks import send_to_channel_callback
from telegram.ext import ChatMemberHandler
from handlers.channel_tracker import track_channels


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(ChatMemberHandler(track_channels, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(CommandHandler("song", song_search))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="track_.*"))
    app.add_handler(CallbackQueryHandler(send_to_channel_callback, pattern="^send_channel_"))
    app.add_handler(MessageHandler(filters.AUDIO, handle_music_file))



    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
