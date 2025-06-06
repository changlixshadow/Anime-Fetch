# ✅ Full working code (Python 3)
# Files needed: posts.json, requests.json
# Requirements: python-telegram-bot >= 20, Flask

import os
import json
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes, ConversationHandler
)

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"
WAITING_FOR_MEDIA, WAITING_FOR_NAME = range(2)
ITEMS_PER_PAGE = 5

START_IMAGE = "https://telegra.ph/file/050a20dace942a60220c0-6afbc023e43fad29c7.jpg"
ABOUT_IMAGE = "https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg"
HELP_IMAGE = "https://telegra.ph/file/e6ec31fc792d072da2b7e-54e7c7d4c5651823b3.jpg"

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

def ensure_file(file):
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def load_json(file):
    ensure_file(file)
    with open(file) as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

# /start with media and buttons
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙️", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    caption = (
        "\u2728 <b>Welcome to Anime Garden!</b> \u2728\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel\n"
    )
    await update.message.reply_photo(photo=START_IMAGE, caption=caption,
                                     parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))

# /help with media and emoji-rich info
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>\u2699 Help Guide</b>\n\n"
        "\u25b6 Use /search <name> to find anime.\n"
        "\u25b6 /animelist to see the list.\n"
        "\u25b6 /requestanime <name> to request new anime.\n\n"
        "<b>Admin Only:</b>\n"
        "\u2714 /addpost\n\u2714 /viewrequests\n"
    )
    await update.message.reply_photo(photo=HELP_IMAGE, caption=caption, parse_mode='HTML')

# About handler
async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    about_caption = (
        "<b>\u2139 About Us</b>\n\n"
        "We are a dedicated Anime uploading community.\n"
        "Check out our partner channels:\n\n"
        "<a href='https://t.me/YourLink1'>\ud83c\udf08 Anime Vault</a>\n"
        "<a href='https://t.me/YourLink2'>\ud83c\udf1f Otaku Corner</a>\n"
        "<a href='https://t.me/YourLink3'>\ud83d\udcf1 Anime X</a>\n"
        "<a href='https://t.me/YourLink4'>\ud83d\ude80 Streaming Hub</a>\n"
        "<a href='https://t.me/YourLink5'>\ud83c\udf10 Global Anime</a>"
    )
    await query.message.edit_media(InputMediaPhoto(media=ABOUT_IMAGE, caption=about_caption, parse_mode='HTML'),
                                   reply_markup=query.message.reply_markup)

# Close handler
async def close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.delete()

# Callback dispatcher
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "about":
        await about_callback(update, context)
    elif data == "help":
        await help_command(update.callback_query, context)
    elif data == "close":
        await close_callback(update, context)

# Catch-all
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help.")

def run():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    app_ = Application.builder().token(API_TOKEN).build()

    # Commands
    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CallbackQueryHandler(callback_handler))
    app_.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot running...")
    app_.run_polling()

if __name__ == '__main__':
    run()
