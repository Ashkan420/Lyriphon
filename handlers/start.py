from telegram import Update
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user else "there"
    
    welcome_text = f"👋 Hello {name}!\n\n" \
                   "I'm your Lyrics & Telegraph bot. Here's what I can do:\n" \
                   "• Send song lyrics via /song <track name>\n" \
                   "• Attach lyrics to music files automatically\n" \
                   "• Create Telegraph pages for tracks\n\n" \
                   "Just start by sending a /song command!"
    
    await update.message.reply_text(welcome_text)
