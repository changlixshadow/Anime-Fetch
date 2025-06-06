from flask import Flask
import os
import json
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

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]  # Admin User IDs here

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

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "𝚆𝚎𝚕𝚌𝚘𝚖𝚎 𝚃𝚘 𝚃𝚑𝚎 𝙰𝚗𝚒𝚖𝚎 𝙶𝚊𝚛𝚍𝚎𝚗! 🚀\n\n"
        "Commands:\n"
        "/search <name> - 𝚂𝚎𝚊𝚛𝚌𝚑 𝙵𝚘𝚛 𝙰𝚗𝚒𝚖𝚎\n"
        "/animelist - 𝚅𝚒𝚎𝚠 𝙰𝚗𝚒𝚖𝚎 𝙻𝚒𝚜𝚝\n"
        "/requestanime <name> - 𝚁𝚎𝚚𝚞𝚎𝚜𝚝 𝙰𝚗𝚒𝚖𝚎\n\n"
        "Admin Commands:\n"
        "/addpost - 𝙰𝚍𝚍 𝙰 𝙽𝚎𝚠 𝙿𝚘𝚜𝚝 (Admin only)\n"
        "/viewrequests - 𝚅𝚒𝚎𝚠 𝚁𝚎𝚚𝚞𝚎𝚜𝚝𝚜 (Admin only)\n"
    )

# Addpost command (admin only)
async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END
    await update.message.reply_text("Send the photo or video with optional caption and buttons.")
    return WAITING_FOR_MEDIA

# Receive media (photo or video)
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
        await update.message.reply_text("𝙿𝚕𝚎𝚊𝚜𝚎 𝚂𝚎𝚗𝚍 𝙰 𝙿𝚑𝚘𝚝𝚘 𝙾𝚛 𝚅𝚒𝚍𝚎𝚘 𝙵𝚒𝚕𝚎.")
        return WAITING_FOR_MEDIA

    caption = update.message.caption or ""
    buttons = []

    # Extract buttons if sent as reply_markup (InlineKeyboardMarkup)
    if update.message.reply_markup and isinstance(update.message.reply_markup, InlineKeyboardMarkup):
        for row in update.message.reply_markup.inline_keyboard:
            buttons.append([{"text": btn.text, "url": btn.url} for btn in row])

    context.user_data.update({
        "media": media,
        "caption": caption,
        "type": media_type,
        "buttons": buttons,
    })

    await update.message.reply_text("𝙿𝚕𝚎𝚊𝚜𝚎 𝚂𝚎𝚗𝚍 𝙰 𝙽𝚊𝚖𝚎 𝙵𝚘𝚛 𝚃𝚑𝚒𝚜 𝙿𝚘𝚜𝚝:")
    return WAITING_FOR_NAME

# Save the post name and data
async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    posts = load_json(POSTS_FILE)

    # Avoid overwriting existing posts if needed (optional)
    # if name in posts:
    #     await update.message.reply_text("This name already exists. Please choose a different name.")
    #     return WAITING_FOR_NAME

    posts[name] = {
        "media": context.user_data["media"],
        "caption": context.user_data["caption"],
        "type": context.user_data["type"],
        "buttons": context.user_data["buttons"],
    }
    save_json(POSTS_FILE, posts)

    await update.message.reply_text(f"𝙿𝚘𝚜𝚝 𝚂𝚊𝚟𝚎𝚍 𝙰𝚜 '{name}'!")
    return ConversationHandler.END

# Pagination helper
def paginate_list(items, page, per_page=ITEMS_PER_PAGE):
    total_pages = (len(items) + per_page - 1) // per_page
    if total_pages == 0:
        total_pages = 1
    if page < 0:
        page = 0
    elif page >= total_pages:
        page = total_pages - 1
    start = page * per_page
    end = start + per_page
    return items[start:end], page, total_pages

# Show animelist command with pagination
async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    if not posts:
        await update.message.reply_text("𝙿𝚘𝚜𝚝𝚜 𝙽𝚘𝚝 𝙵𝚘𝚞𝚗𝚍.")
        return

    sorted_keys = sorted(posts.keys())
    context.user_data["animelist_sorted"] = sorted_keys
    await send_animelist_page(update, context, page=0)

# Send animelist page with inline buttons
async def send_animelist_page(update_or_query, context, page):
    posts = load_json(POSTS_FILE)
    sorted_keys = context.user_data.get("animelist_sorted", sorted(posts.keys()))

    page_items, page, total_pages = paginate_list(sorted_keys, page)

    message = "𝙰𝚗𝚒𝚖𝚎 𝙻𝚒𝚜𝚝:\n━━━━━━━━━━━━━━━━━━\n"
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

# Handle animelist pagination callback
async def animelist_pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith("animelist_page_"):
        return
    page = int(query.data.split("_")[-1])
    await send_animelist_page(query, context, page)

# Search anime by name
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("𝚄𝚜𝚎 /search <anime name>\nExample: /search Naruto")
        return
    name = " ".join(context.args).strip()
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

# Request anime command
async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("𝚄𝚜𝚎: /requestanime <anime name>")
        return

    name = " ".join(context.args).strip()
    requests = load_json(REQUESTS_FILE)
    user_id = str(update.effective_user.id)
    requests.setdefault(user_id, []).append(name)
    save_json(REQUESTS_FILE, requests)

    await update.message.reply_text(f"✅ Your request for '{name}' has been saved!")

# View requests (admin only)
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

# Send requests page with pagination
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

# Requests pagination callback
async def requests_pagination_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith("requests_page_"):
        return
    page = int(query.data.split("_")[-1])
    await send_requests_page(query, context, page)

# Cancel conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Action canceled.")
    return ConversationHandler.END

# Unknown commands handler
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("Unknown command. Use /search or /animelist.")

def run_bot():
    # Ensure JSON files exist
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    # Create bot application
    app_ = Application.builder().token(API_TOKEN).build()

    # Conversation handler for adding posts
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addpost", addpost)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, receive_media)],
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    # Add handlers
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
updater.start_webhook(listen="0.0.0.0",
                      port=int(PORT),
                      url_path=TOKEN)
updater.bot.set_webhook(f"https://anime-fetch-j2ro.onrender.com/{TOKEN}")
