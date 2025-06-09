import os
import json
from flask import Flask, request
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto,
    InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)
from telegram.ext import Defaults
from telegram.constants import ParseMode
import asyncio

# --- Config ---
API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
WEBHOOK_URL = "https://anime-fetch-j2ro.onrender.com/webhook"  # Update with your Render URL
PORT = int(os.environ.get("PORT", 8080))
ADMIN_IDS = [5759232282]

POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"
USERS_FILE = "users.json"
GROUP_CHAT = "@sister_leveling"

START_URL = "https://telegra.ph/file/050a20dace942a60220c0-6afbc023e43fad29c7.jpg"
ABOUT_URL = "https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg"
HELP_URL = "https://telegra.ph/file/e6ec31fc792d072da2b7e-54e7c7d4c5651823b3.jpg"

START_CAPTION = (
    "✨ Welcome to Anime Garden! ✨\n\n"
    "Discover & Request your favorite Anime.\n"
    "Use the buttons below to explore more!\n\n"
    "/addpost\n/animelist\n/search <name>\n/requestanime <name>\n/viewrequests\n/users\n/broadcast\n/cancel"
)
ABOUT_CAPTION = "📜 About Us\n\nAnime Garden is your one-stop destination for discovering and requesting Anime!"
HELP_CAPTION = "⚙️ Help\n\nUse the commands to navigate and request or post anime content."

WAITING_FOR_NAME, WAITING_FOR_BROADCAST = range(2)

# --- Initialize files if not exist ---
for f in [POSTS_FILE, REQUESTS_FILE, USERS_FILE]:
    with open(f, "w") if not os.path.exists(f) else open(f, "r") as fp:
        if not os.path.exists(f):
            json.dump([] if f == REQUESTS_FILE else {}, fp)

# --- Utility ---
def load_data(path):
    with open(path, "r") as f:
        return json.load(f)

def save_data(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("You are not authorized.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper

def extract_buttons(message):
    if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
        return [[{
            "text": b.text,
            "url": b.url if b.url else None,
            "callback_data": b.callback_data if b.callback_data else None
        } for b in row] for row in message.reply_markup.inline_keyboard]
    return None

def build_keyboard(buttons):
    if not buttons: return None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(text=b["text"], url=b.get("url"), callback_data=b.get("callback_data", "noop"))
         for b in row] for row in buttons
    ])

# --- Handlers ---
async def save_user(update: Update):
    users = load_data(USERS_FILE)
    u = update.effective_user
    users[str(u.id)] = {
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
    }
    save_data(USERS_FILE, users)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update)
    buttons = [
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙️", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    await update.message.reply_photo(START_URL, caption=START_CAPTION,
                                     reply_markup=InlineKeyboardMarkup(buttons))

@admin_only
async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message containing media.")
        return ConversationHandler.END
    msg = update.message.reply_to_message
    media_type = "photo" if msg.photo else "document" if msg.document else None
    if not media_type:
        await update.message.reply_text("Supported media: photo/document")
        return ConversationHandler.END
    file_id = msg.photo[-1].file_id if media_type == "photo" else msg.document.file_id
    context.user_data.update({
        "media": {"file_id": file_id, "type": media_type},
        "caption": msg.caption,
        "buttons": extract_buttons(msg)
    })
    await update.message.reply_text("What name to save this post as?")
    return WAITING_FOR_NAME

async def save_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    posts = load_data(POSTS_FILE)
    posts[name] = {
        "media": context.user_data["media"],
        "caption": context.user_data["caption"],
        "buttons": context.user_data["buttons"]
    }
    save_data(POSTS_FILE, posts)
    await update.message.reply_text(f"Saved as '{name}'")
    return ConversationHandler.END

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_data(POSTS_FILE)
    await update.message.reply_text(
        "\n".join(f"• {k}" for k in posts.keys()) or "No posts saved."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = " ".join(context.args).lower()
    if not q: return await update.message.reply_text("Provide search term.")
    posts = load_data(POSTS_FILE)
    results = [k for k in posts if q in k.lower()]
    if not results: return await update.message.reply_text("No matches.")
    for name in results:
        post = posts[name]
        media = post["media"]
        kb = build_keyboard(post.get("buttons"))
        if media["type"] == "photo":
            await update.message.reply_photo(media["file_id"], caption=post["caption"], reply_markup=kb)
        else:
            await update.message.reply_document(media["file_id"], caption=post["caption"], reply_markup=kb)

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    if not text: return await update.message.reply_text("Specify the anime name.")
    requests = load_data(REQUESTS_FILE)
    user = update.effective_user
    requests.append({
        "user_id": user.id,
        "username": user.username,
        "anime": text
    })
    save_data(REQUESTS_FILE, requests)
    await update.message.reply_text(f"Request for '{text}' saved.")
    try:
        await context.bot.send_message(GROUP_CHAT, f"📢 Request from @{user.username or 'user'}:\n{text}")
    except: pass

@admin_only
async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reqs = load_data(REQUESTS_FILE)
    txt = "\n".join(f"@{r['username']}: {r['anime']}" for r in reqs)
    await update.message.reply_text(txt or "No requests.")

@admin_only
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = load_data(USERS_FILE)
    await update.message.reply_text(f"Total users: {len(u)}")

@admin_only
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send the broadcast message.")
    return WAITING_FOR_BROADCAST

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    success = 0
    for uid in users:
        try:
            await context.bot.send_message(int(uid), update.message.text)
            success += 1
        except: pass
    await update.message.reply_text(f"Broadcast sent to {success}/{len(users)} users.")
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "about":
        kb = [[InlineKeyboardButton("Back 🔙", callback_data="back"),
               InlineKeyboardButton("Help ⚙️", callback_data="help")],
              [InlineKeyboardButton("❌ Close", callback_data="close")]]
        await q.edit_message_media(InputMediaPhoto(ABOUT_URL, caption=ABOUT_CAPTION),
                                   reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "help":
        kb = [[InlineKeyboardButton("Back 🔙", callback_data="back"),
               InlineKeyboardButton("About 📜", callback_data="about")],
              [InlineKeyboardButton("❌ Close", callback_data="close")]]
        await q.edit_message_media(InputMediaPhoto(HELP_URL, caption=HELP_CAPTION),
                                   reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "back":
        kb = [[InlineKeyboardButton("About 📜", callback_data="about"),
               InlineKeyboardButton("Help ⚙️", callback_data="help")],
              [InlineKeyboardButton("❌ Close", callback_data="close")]]
        await q.edit_message_media(InputMediaPhoto(START_URL, caption=START_CAPTION),
                                   reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "close":
        await q.delete_message()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Canceled.")
    return ConversationHandler.END

# --- Flask App ---
app = Flask(__name__)
bot_app = Application.builder().token(API_TOKEN).build()

@app.route("/")
def home():
    return "Bot is alive"

@app.route("/webhook", methods=["POST"])
async def webhook():
    await bot_app.update_queue.put(Update.de_json(request.json, bot_app.bot))
    return "ok"

def setup_handlers():
    post_conv = ConversationHandler(
        entry_points=[CommandHandler("addpost", addpost)],
        states={WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_post)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={WAITING_FOR_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    bot_app.add_handler(post_conv)
    bot_app.add_handler(broadcast_conv)
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("animelist", animelist))
    bot_app.add_handler(CommandHandler("search", search))
    bot_app.add_handler(CommandHandler("requestanime", requestanime))
    bot_app.add_handler(CommandHandler("viewrequests", viewrequests))
    bot_app.add_handler(CommandHandler("users", users))
    bot_app.add_handler(CallbackQueryHandler(button_handler))

# --- Run app ---
if __name__ == "__main__":
    setup_handlers()
    loop = asyncio.get_event_loop()
    loop.create_task(bot_app.initialize())
    loop.create_task(bot_app.bot.set_webhook(url=WEBHOOK_URL))
    app.run(host="0.0.0.0", port=PORT)
