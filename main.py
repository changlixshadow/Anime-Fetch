import os
import json
from flask import Flask
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode
import asyncio

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

app = Flask(__name__)

def ensure_file(file):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)

def load_json(file):
    ensure_file(file)
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

async def send_start_banner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("About ℹ️", callback_data="about")],
        [InlineKeyboardButton("Help 🛠️", callback_data="help")],
        [InlineKeyboardButton("Close ❌", callback_data="close")]
    ]
    banner = "https://telegra.ph/file/7e0a1e898edaf94b33c4c.jpg"
    caption = (
        "🎉 <b>Welcome to Anime Garden</b> 🌸\n\n"
        "🔍 Use /search <i>anime name</i> to find posts\n"
        "📜 Browse with /animelist\n"
        "📥 Request anime with /requestanime <i>name</i>\n\n"
        "🔗 Join: <a href='https://t.me/yourchannel'>Our Channel</a>"
    )
    await update.message.reply_photo(
        photo=banner,
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_start_banner(update, context)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "about":
        caption = (
            "<b>About Us</b>\n\n"
            "🌸 Powered by <a href='https://t.me/yourchannel'>Anime Garden</a>\n"
            "🌐 Updates: <a href='https://t.me/yourupdates'>Channel</a>\n"
            "📩 Contact admin: <a href='https://t.me/youradmin'>@youradmin</a>"
        )
        await query.edit_message_caption(
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Help 🛠️", callback_data="help")],
                [InlineKeyboardButton("Close ❌", callback_data="close")]
            ])
        )
    elif query.data == "help":
        help_text = (
            "🛠️ <b>Help Menu</b>\n\n"
            "➤ /search &lt;anime name&gt; - Search posts\n"
            "➤ /animelist - View all anime\n"
            "➤ /requestanime &lt;name&gt; - Request anime\n"
            "➤ /addpost - Admin only, add post\n"
            "➤ /viewrequests - Admin only, view requests\n\n"
            "Bot by @youradmin"
        )
        await query.edit_message_caption(
            caption=help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("About ℹ️", callback_data="about")],
                [InlineKeyboardButton("Close ❌", callback_data="close")]
            ])
        )
    elif query.data == "close":
        await query.delete_message()

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Try /search or /animelist.")

# --- Addpost command - Admin only ---

# We'll store posts in posts.json with keys as unique IDs (e.g. incremental or timestamp)
# Format per post:
# {
#   "id": {
#     "caption": "caption text",
#     "quality": "720p",
#     "genre": "action, fantasy",
#     "episode": "12",
#     "file_id": telegram_file_id,
#     "file_type": "photo" or "video" or "document"
#   },
#   ...
# }

# To simplify, /addpost should be followed by reply to a media with caption containing keys like:
# quality:720p; genre:action; episode:12; caption:Your caption here

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to add posts.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to media with caption containing post info to add.")
        return

    reply = update.message.reply_to_message
    if not (reply.photo or reply.video or reply.document):
        await update.message.reply_text("Reply to a photo, video or document with caption info.")
        return

    # Parse info from reply caption
    text = reply.caption or ""
    # Expected format: quality:720p; genre:action, fantasy; episode:12; caption:My cool caption
    # parse key:value pairs separated by ;
    info = {}
    for part in text.split(";"):
        if ":" in part:
            k,v = part.strip().split(":",1)
            info[k.strip().lower()] = v.strip()

    # Validate minimum keys
    if "caption" not in info:
        await update.message.reply_text("Caption key missing in reply caption.")
        return

    # Load posts
    posts = load_json(POSTS_FILE)

    # Generate new ID
    new_id = str(len(posts)+1)

    # Save media file_id and type
    if reply.photo:
        file_id = reply.photo[-1].file_id  # highest quality photo
        ftype = "photo"
    elif reply.video:
        file_id = reply.video.file_id
        ftype = "video"
    elif reply.document:
        file_id = reply.document.file_id
        ftype = "document"
    else:
        await update.message.reply_text("Unsupported media type.")
        return

    posts[new_id] = {
        "caption": info["caption"],
        "quality": info.get("quality","Unknown"),
        "genre": info.get("genre","Unknown"),
        "episode": info.get("episode","Unknown"),
        "file_id": file_id,
        "file_type": ftype
    }

    save_json(POSTS_FILE, posts)
    await update.message.reply_text(f"✅ Post added with ID {new_id}.")

# --- /search command ---

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).lower()
    if not query:
        await update.message.reply_text("Usage: /search <anime name>")
        return

    posts = load_json(POSTS_FILE)
    results = []
    for pid, post in posts.items():
        if query in post.get("caption","").lower() or query in post.get("genre","").lower():
            results.append((pid, post))

    if not results:
        await update.message.reply_text("No posts found matching your query.")
        return

    for pid, post in results[:5]:  # limit to 5 results
        caption = (
            f"📌 <b>{post['caption']}</b>\n"
            f"Quality: {post['quality']}\n"
            f"Genre: {post['genre']}\n"
            f"Episode: {post['episode']}"
        )
        # Send media with caption
        if post["file_type"] == "photo":
            await update.message.reply_photo(photo=post["file_id"], caption=caption, parse_mode=ParseMode.HTML)
        elif post["file_type"] == "video":
            await update.message.reply_video(video=post["file_id"], caption=caption, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_document(document=post["file_id"], caption=caption, parse_mode=ParseMode.HTML)

# --- /animelist command with simple pagination ---

PAGE_SIZE = 3

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    if not posts:
        await update.message.reply_text("No posts available yet.")
        return

    # page number from args or 0
    page = 0
    if context.args and context.args[0].isdigit():
        page = int(context.args[0])

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    items = list(posts.items())[start:end]

    text = "<b>Anime List</b>\n\n"
    buttons = []
    for pid, post in items:
        text += f"{pid}. {post['caption']} ({post['quality']})\n"
        buttons.append([InlineKeyboardButton(f"View {pid}", callback_data=f"viewpost_{pid}")])

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"animelist_{page-1}"))
    if end < len(posts):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"animelist_{page+1}"))

    reply_markup = InlineKeyboardMarkup(buttons + [nav_buttons] if nav_buttons else buttons)

    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def animelist_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # animelist_0 or animelist_1

    if not data.startswith("animelist_"):
        return
    page = int(data.split("_")[1])

    posts = load_json(POSTS_FILE)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    items = list(posts.items())[start:end]

    text = "<b>Anime List</b>\n\n"
    buttons = []
    for pid, post in items:
        text += f"{pid}. {post['caption']} ({post['quality']})\n"
        buttons.append([InlineKeyboardButton(f"View {pid}", callback_data=f"viewpost_{pid}")])

    nav_buttons = []
    if start > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"animelist_{page-1}"))
    if end < len(posts):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"animelist_{page+1}"))

    reply_markup = InlineKeyboardMarkup(buttons + [nav_buttons] if nav_buttons else buttons)

    await query.edit_message_text(text=text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# --- View single post from animelist ---

async def viewpost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data  # viewpost_1

    if not data.startswith("viewpost_"):
        return

    pid = data.split("_")[1]
    posts = load_json(POSTS_FILE)
    post = posts.get(pid)
    if not post:
        await query.edit_message_text("Post not found.")
        return

    caption = (
        f"📌 <b>{post['caption']}</b>\n"
        f"Quality: {post['quality']}\n"
        f"Genre: {post['genre']}\n"
        f"Episode: {post['episode']}"
    )

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Back to List", callback_data="animelist_0")]
    ])

    if post["file_type"] == "photo":
        media = InputMediaPhoto(media=post["file_id"], caption=caption, parse_mode=ParseMode.HTML)
    elif post["file_type"] == "video":
        media = post["file_id"]  # will send video separately
    else:
        media = post["file_id"]

    # Edit message with text + buttons
    # Telegram limits editing media + caption simultaneously, so better just edit caption and buttons
    await query.edit_message_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=kb)

# --- /requestanime command ---

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text("Usage: /requestanime <anime name>")
        return

    requests = load_json(REQUESTS_FILE)

    req_id = str(len(requests)+1)
    requests[req_id] = {
        "user_id": user.id,
        "user_name": user.username or user.full_name,
        "request": query
    }
    save_json(REQUESTS_FILE, requests)
    await update.message.reply_text(f"✅ Your request for '{query}' has been received!")

# --- /viewrequests (admin only) ---

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized.")
        return

    requests = load_json(REQUESTS_FILE)
    if not requests:
        await update.message.reply_text("No requests yet.")
        return

    text = "<b>Anime Requests</b>\n\n"
    for rid, req in requests.items():
        text += f"{rid}. @{req['user_name']}: {req['request']}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# --- /help command ---

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠️ <b>Help Menu</b>\n\n"
        "➤ /search &lt;anime name&gt; - Search posts\n"
        "➤ /animelist - View all anime\n"
        "➤ /requestanime &lt;name&gt; - Request anime\n"
        "➤ /addpost - Admin only, add post\n"
        "➤ /viewrequests - Admin only, view requests\n"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# --- Main ---

async def main():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    application = Application.builder().token(API_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addpost", addpost))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("animelist", animelist))
    application.add_handler(CommandHandler("requestanime", requestanime))
    application.add_handler(CommandHandler("viewrequests", viewrequests))

    application.add_handler(CallbackQueryHandler(callback_handler, pattern="^(about|help|close)$"))
    application.add_handler(CallbackQueryHandler(animelist_callback, pattern=r"^animelist_\d+$"))
    application.add_handler(CallbackQueryHandler(viewpost_callback, pattern=r"^viewpost_\d+$"))

    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Bot started!")
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
