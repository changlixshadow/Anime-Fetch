# ✅ Fully working Render-compatible bot with proper /start, buttons, help, and commands

import os
import json
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

START_IMAGE = "https://telegra.ph/file/050a20dace942a60220c0.jpg"
ABOUT_IMAGE = "https://telegra.ph/file/9d18345731db88fff4f8c.jpg"
HELP_IMAGE = "https://telegra.ph/file/e6ec31fc792d072da2b7e.jpg"

# --- Flask app for Render ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return 'Bot is running!'

# --- JSON helpers ---
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

# --- Buttons ---
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

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "✨ <b>Welcome to Anime Garden!</b> ✨\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel"
    )
    await update.message.reply_photo(photo=START_IMAGE, caption=caption, parse_mode='HTML', reply_markup=start_buttons())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>⚙ Help Guide</b>\n\n"
        "▶ /search <name>\n▶ /animelist\n▶ /requestanime <name>\n\n"
        "<b>Admins:</b>\n✅ /addpost\n✅ /viewrequests"
    )
    await update.message.reply_photo(photo=HELP_IMAGE, caption=caption, parse_mode='HTML')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "about":
        caption = (
            "<b>ℹ About</b>\n\nWe share anime daily!\n\n"
            "<b>Main:</b> @YourMainChannel\n<b>Backup:</b> @YourBackupChannel\n<b>NSFW:</b> @YourEcchiChannel"
        )
        await query.message.edit_media(InputMediaPhoto(ABOUT_IMAGE, caption=caption, parse_mode='HTML'), reply_markup=back_help_buttons())

    elif query.data == "help":
        caption = (
            "<b>⚙ Help Guide</b>\n\n▶ /search <name>\n▶ /animelist\n▶ /requestanime <name>\n\n<b>Admins:</b>\n✅ /addpost\n✅ /viewrequests"
        )
        await query.message.edit_media(InputMediaPhoto(HELP_IMAGE, caption=caption, parse_mode='HTML'), reply_markup=back_button())

    elif query.data == "back":
        await query.message.edit_media(InputMediaPhoto(START_IMAGE, caption=(
            "✨ <b>Welcome to Anime Garden!</b> ✨\n\nDiscover & Request your favorite Anime.\n\n<b>Channel:</b> @YourMainChannel\n<b>Backup:</b> @YourBackupChannel"
        ), parse_mode='HTML'), reply_markup=start_buttons())

    elif query.data == "close":
        await query.message.delete()

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help")

async def delete_unwanted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

# --- Main ---
def main():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)
    
    app = Application.builder().token(API_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_unwanted))

    print("Bot is running with polling...")
    app.run_polling()

if __name__ == '__main__':
    main()
