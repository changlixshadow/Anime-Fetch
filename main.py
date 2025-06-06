import os
import json
import ssl
import certifi
from flask import Flask, request, abort
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode
import asyncio

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]

POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

START_IMAGE = "https://telegra.ph/file/050a20dace942a60220c0.jpg"
ABOUT_IMAGE = "https://telegra.ph/file/9d18345731db88fff4f8c.jpg"
HELP_IMAGE = "https://telegra.ph/file/e6ec31fc792d072da2b7e.jpg"

WEBHOOK_URL_BASE = "https://anime-fetch-j2ro.onrender.com"
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"

# Flask app
flask_app = Flask(__name__)

def ensure_file(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load_json(file):
    ensure_file(file)
    with open(file) as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def start_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙️", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

def back_help_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back"),
         InlineKeyboardButton("Help ⚙️", callback_data="help")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "✨ <b>Welcome to Anime Garden!</b> ✨\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel"
    )
    await update.message.reply_photo(photo=START_IMAGE, caption=caption, parse_mode=ParseMode.HTML, reply_markup=start_buttons())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>⚙ Help Guide</b>\n\n"
        "▶ /search &lt;name&gt;\n▶ /animelist\n▶ /requestanime &lt;name&gt;\n\n"
        "<b>Admins:</b>\n✅ /addpost\n✅ /viewrequests"
    )
    await update.message.reply_photo(photo=HELP_IMAGE, caption=caption, parse_mode=ParseMode.HTML)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "about":
        caption = (
            "<b>ℹ About</b>\n\nWe share anime daily!\n\n"
            "<b>Main:</b> @YourMainChannel\n<b>Backup:</b> @YourBackupChannel\n<b>NSFW:</b> @YourEcchiChannel"
        )
        await query.message.edit_media(InputMediaPhoto(ABOUT_IMAGE, caption=caption, parse_mode=ParseMode.HTML), reply_markup=back_help_buttons())

    elif query.data == "help":
        caption = (
            "<b>⚙ Help Guide</b>\n\n▶ /search &lt;name&gt;\n▶ /animelist\n▶ /requestanime &lt;name&gt;\n\n<b>Admins:</b>\n✅ /addpost\n✅ /viewrequests"
        )
        await query.message.edit_media(InputMediaPhoto(HELP_IMAGE, caption=caption, parse_mode=ParseMode.HTML), reply_markup=back_button())

    elif query.data == "back":
        await query.message.edit_media(InputMediaPhoto(START_IMAGE, caption=(
            "✨ <b>Welcome to Anime Garden!</b> ✨\n\nDiscover & Request your favorite Anime.\n\n<b>Channel:</b> @YourMainChannel\n<b>Backup:</b> @YourBackupChannel"
        ), parse_mode=ParseMode.HTML), reply_markup=start_buttons())

    elif query.data == "close":
        await query.message.delete()

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help")

async def delete_unwanted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

# Setup Telegram bot Application
app = ApplicationBuilder().token(API_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CallbackQueryHandler(button_callback))
app.add_handler(MessageHandler(filters.COMMAND, unknown))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_unwanted))

# Flask routes
@flask_app.route('/')
def home():
    return "Bot is running!"

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), app.bot)
        asyncio.run(app.update_queue.put(update))
        return "OK"
    else:
        abort(405)

if __name__ == "__main__":
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    async def main_async():
        await app.initialize()
        await app.start()

        # Set webhook with certifi SSL context (if needed)
        success = await app.bot.set_webhook(WEBHOOK_URL_BASE + WEBHOOK_PATH)
        print("Webhook set:", success)

    # Run async bot startup + webhook set
    asyncio.run(main_async())

    # Start Flask webserver for Render
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
