from flask import Flask
import threading
import asyncio
import json
import os

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_ID = 5759232282
POSTS_FILE = "posts.json"
WAITING_FOR_MEDIA, WAITING_FOR_NAME = range(2)

# ----------------- Flask Setup ----------------- #
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

# ----------------- File Handling ----------------- #
def ensure_posts_file():
    if not os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, "w") as f:
            json.dump({}, f)

def save_post(name, data):
    ensure_posts_file()
    with open(POSTS_FILE, "r") as f:
        posts = json.load(f)
    posts[name] = data
    with open(POSTS_FILE, "w") as f:
        json.dump(posts, f, indent=4)

def load_posts():
    ensure_posts_file()
    with open(POSTS_FILE, "r") as f:
        return json.load(f)

# ----------------- Telegram Bot Handlers ----------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Anime Bot! 🚀\n\n"
        "Commands:\n"
        "/addpost - Add a new anime post (Admin only)\n"
        "/search <name> - Search for an anime\n"
        "/animelist - View the list of saved anime\n"
    )

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END

    await update.message.reply_text("Send the photo or video with optional caption and buttons.")
    return WAITING_FOR_MEDIA

async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media = None
    media_type = None

    if update.message.photo:
        media = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        media = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text("Send a photo or video.")
        return WAITING_FOR_MEDIA

    caption = update.message.caption or ""
    buttons = []
    if update.message.reply_markup and isinstance(update.message.reply_markup, InlineKeyboardMarkup):
        for row in update.message.reply_markup.inline_keyboard:
            buttons.append([{"text": btn.text, "url": btn.url} for btn in row])

    context.user_data.update({
        "media": media,
        "caption": caption,
        "type": media_type,
        "buttons": buttons
    })

    await update.message.reply_text("What name should I save this as?")
    return WAITING_FOR_NAME

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    data = {
        "media": context.user_data["media"],
        "caption": context.user_data["caption"],
        "type": context.user_data["type"],
        "buttons": context.user_data["buttons"]
    }
    save_post(name, data)
    await update.message.reply_text(f"Post saved as '{name}'!")
    return ConversationHandler.END

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_posts()
    if not posts:
        await update.message.reply_text("No anime saved yet.")
        return

    sorted_posts = sorted(posts.keys())
    msg = "Saved Anime List:\n\n"
    current_letter = None
    for name in sorted_posts:
        first_letter = name[0].upper()
        if first_letter != current_letter:
            current_letter = first_letter
            msg += f"\n*{current_letter}*\n"
        msg += f" - {name}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a name to search.")
        return

    name = " ".join(context.args)
    posts = load_posts()
    post = posts.get(name)

    if post:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(btn["text"], url=btn["url"]) for btn in row] for row in post.get("buttons", [])]
        )
        if post["type"] == "photo":
            await update.message.reply_photo(post["media"], caption=post["caption"], reply_markup=markup)
        else:
            await update.message.reply_video(post["media"], caption=post["caption"], reply_markup=markup)
    else:
        await update.message.reply_text("No post found with that name.")

async def handle_unrecognized(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Unrecognized command.\n"
            "Use /search <name> or /animelist to see available anime."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Action canceled.")
    return ConversationHandler.END

# ----------------- Bot Runner ----------------- #
async def main_bot():
    ensure_posts_file()
    application = Application.builder().token(API_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addpost", addpost)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, receive_media)],
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("animelist", animelist))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.ALL, handle_unrecognized, block=False))

    print("Bot started 🚀")
    await application.run_polling()

def run_bot():
    asyncio.run(main_bot())

# ----------------- Main Entry ----------------- #
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
