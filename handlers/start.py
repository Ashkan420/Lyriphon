from telegram import Update
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user else "there"
    
    welcome_text = (
        f"Hello {name}!\n\n"
        "I'm your Lyrics & Telegraph bot. Here's what I can do:\n"
        "• Send song lyrics via /song\n"
        "• Attach lyrics to music files automatically\n"
        "• Create Telegraph pages for tracks\n\n"
        "Type /help for a full list of commands."
    )
    
    await update.message.reply_text(welcome_text)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        f"Lyriphon Bot Commands\n\n"
        "/song - Search for a song and create a lyrics page\n"
        "/help - Show this help message\n\n"
        "How to use:\n"
        "1. Search with /song\n"
        "2. Pick a track from the results\n"
        "3. Send a music file in this chat to attach the Lyrics button\n"
        "4. Send it to any channel where I'm an admin\n\n"
        "Inline mode:\n"
        "Type @lyriphon_bot in any chat to search directly."
    )
    
    await update.message.reply_text(help_text)
