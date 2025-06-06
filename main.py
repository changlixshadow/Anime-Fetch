import os
import json
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

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

# Buttons helper functions
def start_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙️", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "\u2728 <b>Welcome to Anime Garden!</b> \u2728\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel\n"
    )
    await update.message.reply_photo(photo=START_IMAGE, caption=caption,
                                     parse_mode='HTML', reply_markup=start_buttons())

# /help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>\u2699 Help Guide</b>\n\n"
        "\u25b6 Use /search &lt;name&gt; to find anime.\n"
        "\u25b6 /animelist to see the list.\n"
        "\u25b6 /requestanime &lt;name&gt; to request new anime.\n\n"
        "<b>Admin Only:</b>\n"
        "\u2714 /addpost\n\u2714 /viewrequests\n"
    )
    # If called as a command (normal message)
    if update.message:
        await update.message.reply_photo(photo=HELP_IMAGE, caption=caption, parse_mode='HTML')
    # If called from callback query, edit media instead
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.message.edit_media(
            InputMediaPhoto(media=HELP_IMAGE, caption=caption, parse_mode='HTML'),
            reply_markup=back_button()
        )

# About button handler
async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    about_caption = (
        "<b>\u2139 About Us</b>\n\n"
        "We are a dedicated Anime uploading community.\n"
        "Check out our partner channels:\n\n"
        "<a href='https://t.me/YourLink1'>🌈 Anime Vault</a>\n"
        "<a href='https://t.me/YourLink2'>🌟 Otaku Corner</a>\n"
        "<a href='https://t.me/YourLink3'>📱 Anime X</a>\n"
        "<a href='https://t.me/YourLink4'>🚀 Streaming Hub</a>\n"
        "<a href='https://t.me/YourLink5'>🌐 Global Anime</a>"
    )
    await query.message.edit_media(
        InputMediaPhoto(media=ABOUT_IMAGE, caption=about_caption, parse_mode='HTML'),
        reply_markup=back_button()
    )

# Close button handler
async def close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.delete()

# Back button handler
async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    caption = (
        "\u2728 <b>Welcome to Anime Garden!</b> \u2728\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel\n"
    )
    await query.message.edit_media(
        InputMediaPhoto(media=START_IMAGE, caption=caption, parse_mode='HTML'),
        reply_markup=start_buttons()
    )

# Callback query handler dispatcher
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "about":
        await about_callback(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "close":
        await close_callback(update, context)
    elif data == "back":
        await back_callback(update, context)

# Catch-all unknown command handler
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help.")

def run():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    app_ = Application.builder().token(API_TOKEN).build()

    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CallbackQueryHandler(callback_handler))
    app_.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot running...")
    app_.run_polling()

if __name__ == '__main__':
    run()
