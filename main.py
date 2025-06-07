import os
import json
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
import asyncio

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://anime-fetch-j2ro.onrender.com{WEBHOOK_PATH}"

POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"
WAITING_FOR_MEDIA, WAITING_FOR_NAME = range(2)
ITEMS_PER_PAGE = 5

app = Flask(__name__)

# Build application object
application = Application.builder().token(API_TOKEN).build()

@app.route("/")
def home():
    return "✅ Bot is alive with webhook!"

@app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
    return "ok"

# Utility functions
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

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome to the Anime Bot!\nUse /addpost, /search, /animelist, etc.")

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 You are not authorized.")
        return ConversationHandler.END
    await update.message.reply_text("📤 Send the photo or video with a caption and buttons (optional).")
    return WAITING_FOR_MEDIA

async def receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    media, media_type = None, None
    if update.message.photo:
        media = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        media = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text("❌ Please send a photo or video.")
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
        "buttons": buttons,
    })

    await update.message.reply_text("💾 Enter a name to save this post as:")
    return WAITING_FOR_NAME

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    posts = load_json(POSTS_FILE)
    posts[name] = context.user_data.copy()
    save_json(POSTS_FILE, posts)
    await update.message.reply_text(f"✅ Post saved as: {name}")
    return ConversationHandler.END

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <name>")
        return
    name = " ".join(context.args)
    posts = load_json(POSTS_FILE)
    if name not in posts:
        await update.message.reply_text("❌ No post found.")
        return

    post = posts[name]
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row] for row in post.get("buttons", [])]
    )

    if post["type"] == "photo":
        await update.message.reply_photo(post["media"], caption=post["caption"], reply_markup=markup)
    else:
        await update.message.reply_video(post["media"], caption=post["caption"], reply_markup=markup)

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    if not posts:
        await update.message.reply_text("No anime saved yet.")
        return
    names = sorted(posts.keys())
    message = "\n".join(f"• {name}" for name in names)
    await update.message.reply_text(f"📚 Saved Anime List:\n{message}")

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /requestanime <anime name>")
        return
    name = " ".join(context.args)
    requests = load_json(REQUESTS_FILE)
    user_id = str(update.effective_user.id)
    requests.setdefault(user_id, []).append(name)
    save_json(REQUESTS_FILE, requests)
    await update.message.reply_text(f"📩 Request saved for: {name}")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Not authorized.")
        return
    requests = load_json(REQUESTS_FILE)
    if not requests:
        await update.message.reply_text("No requests found.")
        return
    msg = "\n".join(f"User {uid}: {', '.join(animes)}" for uid, animes in requests.items())
    await update.message.reply_text(f"📋 Requests:\n{msg}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Try /search or /animelist.")

# Register Handlers
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("addpost", addpost)],
    states={
        WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, receive_media)],
        WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("search", search))
application.add_handler(CommandHandler("animelist", animelist))
application.add_handler(CommandHandler("requestanime", requestanime))
application.add_handler(CommandHandler("viewrequests", viewrequests))
application.add_handler(conv_handler)
application.add_handler(MessageHandler(filters.COMMAND, unknown))

# Webhook setup
async def set_webhook():
    await application.bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook set to {WEBHOOK_URL}")

if __name__ == '__main__':
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)
    asyncio.run(set_webhook())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
