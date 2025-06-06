# ✅ Full working Render-compatible anime bot with banner, post system, and commands

import os
import json
from flask import Flask
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"
WAITING_FOR_MEDIA, WAITING_FOR_NAME = range(2)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def ensure_file(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

def load_json(file):
    ensure_file(file)
    with open(file, "r") as f:
        return json.load(f)

START_BANNER_URL = "https://telegra.ph/file/2e3bff6ea7852419eeb6c.jpg"
ABOUT_BANNER_URL = "https://telegra.ph/file/9b25d84c3f0d6ae6850d9.jpg"
HELP_BANNER_URL = "https://telegra.ph/file/b87b9c872f2705026dd67.jpg"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("\ud83d\udcd6 About", callback_data="about")],
        [InlineKeyboardButton("\ud83c\udd98 Help", callback_data="help")],
        [InlineKeyboardButton("\u274c Close", callback_data="close")]
    ]
    await update.message.reply_photo(
        photo=START_BANNER_URL,
        caption=(
            "\ud83d\udc4b \u1d0d\u1d04\u1d07\u1d0b\u1d07 \u1d05\u1d0f \u1d1b\u1d00 \u1d1d\u1d07\u1d07 \u1d05\u1d0f \u1d18\u1d07 \u1d0d\u1d07 \u1d0d\u1d07\u026a\u1d04 \u1d0b\u1d00\u1d07\u1d04\u1d07\u1d0d\n\n"
            "\ud83d\udd0d /search <name>\n"
            "\ud83d\udcdc /animelist\n"
            "\ud83c\udfaf /requestanime <title>"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "about":
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=ABOUT_BANNER_URL,
                caption=(
                    "\ud83d\udcd6 <b>About Us</b>\n\n"
                    "We are a team of otakus bringing you the best anime collection!\n"
                    "\ud83d\udcfa <a href='https://t.me/anime_channel'>Our Channel</a>\n"
                    "\ud83c\udf10 <a href='https://t.me/anime_support'>Support</a>\n"
                    "\ud83c\udfae <a href='https://t.me/anime_games'>Games</a>"
                ),
                parse_mode="HTML"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("\ud83d\udd19 Back", callback_data="back")]
            ])
        )
        await query.answer()
    elif data == "help":
        await query.edit_message_media(
            media=InputMediaPhoto(
                media=HELP_BANNER_URL,
                caption=(
                    "\ud83c\udd98 <b>Help Section</b>\n\n"
                    "\ud83d\udd0d /search <name> - Search anime by name\n"
                    "\ud83d\udcdc /animelist - View all available anime\n"
                    "\ud83c\udfaf /requestanime <name> - Request new anime\n\n"
                    "Admins:\n"
                    "\u2795 /addpost - Add a post\n"
                    "\ud83d\udcec /viewrequests - View requests"
                ),
                parse_mode="HTML"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("\ud83d\udd19 Back", callback_data="back")]
            ])
        )
        await query.answer()
    elif data == "back":
        await start(update, context)
    elif data == "close":
        await query.message.delete()

# -------------------- Addpost, Request, Search, Animelist --------------------

async def addpost_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return ConversationHandler.END
    await update.message.reply_text("Send the media to post:")
    return WAITING_FOR_MEDIA

async def addpost_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['media'] = update.message
    await update.message.reply_text("Now send the name/label for the post:")
    return WAITING_FOR_NAME

async def addpost_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    media_msg = context.user_data['media']
    posts = load_json(POSTS_FILE)

    post_data = {
        "caption": media_msg.caption or name,
        "file_id": media_msg.video.file_id if media_msg.video else media_msg.document.file_id,
        "type": "video" if media_msg.video else "document"
    }
    posts[name] = post_data
    save_json(POSTS_FILE, posts)

    await update.message.reply_text(f"Post saved as: {name}")
    return ConversationHandler.END

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    if not posts:
        await update.message.reply_text("No anime posts yet.")
        return
    msg = "\ud83d\udcd6 <b>Available Anime</b>\n\n"
    for name in posts:
        msg += f"• {name}\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <name>")
        return
    query = " ".join(context.args).lower()
    posts = load_json(POSTS_FILE)
    for name, data in posts.items():
        if query in name.lower():
            if data['type'] == 'video':
                await update.message.reply_video(video=data['file_id'], caption=data['caption'])
            else:
                await update.message.reply_document(document=data['file_id'], caption=data['caption'])
            return
    await update.message.reply_text("Not found.")

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /requestanime <title>")
        return
    title = " ".join(context.args)
    requests = load_json(REQUESTS_FILE)
    requests[str(update.effective_user.id)] = title
    save_json(REQUESTS_FILE, requests)
    await update.message.reply_text("Your request has been noted.")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized.")
        return
    requests = load_json(REQUESTS_FILE)
    if not requests:
        await update.message.reply_text("No requests yet.")
        return
    msg = "\ud83d\udce3 <b>User Requests</b>\n\n"
    for uid, title in requests.items():
        msg += f"User {uid}: {title}\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# -------------------- Run Bot --------------------

def run_bot():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)
    
    app_ = Application.builder().token(API_TOKEN).build()

    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CallbackQueryHandler(button_handler, pattern="^(about|help|back|close)$"))

    app_.add_handler(CommandHandler("animelist", animelist))
    app_.add_handler(CommandHandler("search", search))
    app_.add_handler(CommandHandler("requestanime", requestanime))
    app_.add_handler(CommandHandler("viewrequests", viewrequests))

    addpost_conv = ConversationHandler(
        entry_points=[CommandHandler("addpost", addpost_start)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.VIDEO | filters.Document.ALL, addpost_media)],
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, addpost_name)]
        },
        fallbacks=[]
    )
    app_.add_handler(addpost_conv)

    print("\u2705 Bot running with polling...")
    app_.run_polling()

if __name__ == "__main__":
    run_bot()
