from flask import Flask
import threading
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import json
import os

API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
ADMIN_IDS = [5759232282]  # Add admin user IDs here

POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

WAITING_FOR_MEDIA, WAITING_FOR_NAME = range(2)

ITEMS_PER_PAGE = 5

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

# Telegram bot handlers (same as you gave)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Anime Bot! 🚀\n\n"
        "Commands:\n"
        "/addpost - Add a new anime post (Admin only)\n"
        "/search <name> - Search for an anime\n"
        "/animelist - View the list of saved anime\n"
        "/requestanime <name> - Request an anime\n"
        "/viewrequests - View user requests (Admin only)\n"
    )

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END
    await update.message.reply_text("Send the photo or video with optional caption and buttons.")
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
        await update.message.reply_text("Please send a photo or video.")
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

    await update.message.reply_text("Enter a name to save this post:")
    return WAITING_FOR_NAME

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    posts = load_json(POSTS_FILE)
    posts[name] = {
        "media": context.user_data["media"],
        "caption": context.user_data["caption"],
        "type": context.user_data["type"],
        "buttons": context.user_data["buttons"],
    }
    save_json(POSTS_FILE, posts)

    await update.message.reply_text(f"Post saved as '{name}'!")
    return ConversationHandler.END

def paginate_list(items, page, per_page=ITEMS_PER_PAGE):
    total_pages = (len(items) + per_page - 1) // per_page
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1
    start = page * per_page
    end = start + per_page
    return items[start:end], page, total_pages

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    if not posts:
        await update.message.reply_text("No anime saved yet.")
        return

    context.user_data["animelist_sorted"] = sorted(posts.keys())
    await send_animelist_page(update, context, page=0)

async def send_animelist_page(update_or_query, context, page):
    posts = load_json(POSTS_FILE)
    sorted_keys = context.user_data.get("animelist_sorted", sorted(posts.keys()))

    page_items, page, total_pages = paginate_list(sorted_keys, page)

    message = "Saved Anime List:\n"
    current_letter = None
    for name in page_items:
        first_letter = name[0].upper()
        if first_letter != current_letter:
            current_letter = first_letter
            message += f"\n*{current_letter}*\n"
        message += f" - {name}\n"

    keyboard = []
    if total_pages > 1:
        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"animelist_page_{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"animelist_page_{page+1}"))
        keyboard.append(buttons)

    markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(message, parse_mode="Markdown", reply_markup=markup)
    else:
        await update_or_query.edit_message_text(message, parse_mode="Markdown", reply_markup=markup)
        await update_or_query.answer()

async def animelist_pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith("animelist_page_"):
        return
    page = int(query.data.split("_")[-1])
    await send_animelist_page(query, context, page)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search <name>")
        return
    name = " ".join(context.args)
    posts = load_json(POSTS_FILE)
    if name not in posts:
        await update.message.reply_text("No post found with that name.")
        return

    post = posts[name]
    markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row]
         for row in post.get("buttons", [])]
    )

    if post["type"] == "photo":
        await update.message.reply_photo(photo=post["media"], caption=post["caption"], reply_markup=markup)
    else:
        await update.message.reply_video(video=post["media"], caption=post["caption"], reply_markup=markup)

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /requestanime <anime name>")
        return

    name = " ".join(context.args)
    requests = load_json(REQUESTS_FILE)
    user_id = str(update.effective_user.id)
    requests.setdefault(user_id, []).append(name)
    save_json(REQUESTS_FILE, requests)

    await update.message.reply_text(f"✅ Your request for '{name}' has been saved!")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to view requests.")
        return

    requests = load_json(REQUESTS_FILE)
    if not requests:
        await update.message.reply_text("No requests found.")
        return

    requests_list = []
    for user_id, animes in requests.items():
        for anime in animes:
            requests_list.append((user_id, anime))

    context.user_data["requests_list"] = requests_list
    await send_requests_page(update, context, page=0)

async def send_requests_page(update_or_query, context, page):
    requests_list = context.user_data.get("requests_list", [])
    page_items, page, total_pages = paginate_list(requests_list, page)

    message = "User Anime Requests:\n\n"
    for user_id, anime in page_items:
        message += f"User ID: `{user_id}` — {anime}\n"

    keyboard = []
    if total_pages > 1:
        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"requests_page_{page-1}"))
        if page < total_pages - 1:
            buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"requests_page_{page+1}"))
        keyboard.append(buttons)

    markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(message, parse_mode="Markdown", reply_markup=markup)
    else:
        await update_or_query.edit_message_text(message, parse_mode="Markdown", reply_markup=markup)
        await update_or_query.answer()

async def requests_pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith("requests_page_"):
        return
    page = int(query.data.split("_")[-1])
    await send_requests_page(query, context, page)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Action canceled.")
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Unknown command. Use /search or /animelist.")

def run_bot():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    app_ = Application.builder().token(API_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addpost", addpost)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, receive_media)],
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CommandHandler("animelist", animelist))
    app_.add_handler(CallbackQueryHandler(animelist_pagination_handler, pattern=r"^animelist_page_\d+$"))
    app_.add_handler(CommandHandler("search", search))
    app_.add_handler(CommandHandler("requestanime", requestanime))
    app_.add_handler(CommandHandler("viewrequests", viewrequests))
    app_.add_handler(CallbackQueryHandler(requests_pagination_handler, pattern=r"^requests_page_\d+$"))
    app_.add_handler(conv_handler)
    app_.add_handler(MessageHandler(filters.ALL, unknown, block=False))

    print("Bot is running 🚀")
    app_.run_polling()

if __name__ == "__main__":
    run_bot()
