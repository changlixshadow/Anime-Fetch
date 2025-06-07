import os
import json
from flask import Flask, request
from telegram import (
    Bot, Update, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode
import asyncio

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_ID = 5759232282
BOT_USERNAME = "@Anime_fetch_robot"  # Optional: Set if you use inline mention

POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

app = Flask(__name__)
bot = Bot(token=API_TOKEN)

# Ensure JSON files exist
for file in [POSTS_FILE, REQUESTS_FILE]:
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump({}, f)


# --- Start Message ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 About", callback_data="about"),
         InlineKeyboardButton("❓ Help", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    await update.message.reply_photo(
        photo="https://telegra.ph/file/050a20dace942a60220c0-6afbc023e43fad29c7.jpg",
        caption="🎌 <b>Welcome to AnimeZone Bot!</b>\n\n"
                "Find and request anime, or explore our collection using /search and /animelist.\n\n"
                "Join our channel 👉 @YourChannelName",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- Help/About Callback ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "about":
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="start"),
             InlineKeyboardButton("❓ Help", callback_data="help")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]
        await query.message.edit_media(
            media=InputMediaPhoto(
                media="https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg",
                caption="ℹ️ <b>About Us</b>\n\n"
                        "We are passionate about sharing high-quality anime with fans! 🎥\n"
                        "Join our community: <a href='https://t.me/YourChannelName'>@YourChannelName</a>",
                parse_mode=ParseMode.HTML
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "help":
        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="start"),
             InlineKeyboardButton("📖 About", callback_data="about")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ]
        await query.message.edit_media(
            media=InputMediaPhoto(
                media="https://telegra.ph/file/e6ec31fc792d072da2b7e-54e7c7d4c5651823b3.jpg",
                caption="❓ <b>Help Guide</b>\n\n"
                        "🔍 <b>/search</b> <i>name</i> – Search for saved anime\n"
                        "📥 <b>/addpost</b> – Add anime post (admin only)\n"
                        "📃 <b>/animelist</b> – Show all saved anime\n"
                        "💬 <b>/requestanime</b> <i>name</i> – Request anime\n"
                        "🧾 <b>/viewrequests</b> – View your requests\n",
                parse_mode=ParseMode.HTML
            ),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "start":
        await start(update, context)
    elif query.data == "close":
        await query.message.delete()


# --- Add Post ---
user_data = {}

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You can't use admin command.")
        return
    await update.message.reply_text("📥 Please send the post (media + caption + buttons).")
    user_data[update.effective_user.id] = {"state": "awaiting_post"}

async def handle_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_data and user_data[user_id].get("state") == "awaiting_post":
        user_data[user_id]["post"] = update.message.to_dict()
        user_data[user_id]["state"] = "awaiting_name"
        await update.message.reply_text("✏️ Now send the name to save this post as:")
    elif user_id in user_data and user_data[user_id].get("state") == "awaiting_name":
        name = update.message.text.strip().lower()
        with open(POSTS_FILE, "r+") as f:
            data = json.load(f)
            data[name] = user_data[user_id]["post"]
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()
        await update.message.reply_text(f"✅ Post saved as: <b>{name}</b>", parse_mode=ParseMode.HTML)
        user_data.pop(user_id)


# --- Search ---
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) == 0:
        await update.message.reply_text("❗ Usage: /search <name>")
        return
    name = " ".join(context.args).lower()
    with open(POSTS_FILE) as f:
        data = json.load(f)
    if name not in data:
        await update.message.reply_text("😢 No post found with that name.")
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📤 Here is the post you searched for:",
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        **data[name]
    )


# --- Flask Webhook Route (for Render or local) ---
@app.route(f"/{API_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await application.update_queue.put(update)
    return "ok"


@app.route("/")
def home():
    return "✅ Bot is running!"


# --- Bot Setup ---
application = Application.builder().token(API_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", start))
application.add_handler(CallbackQueryHandler(button_callback))
application.add_handler(CommandHandler("addpost", addpost))
application.add_handler(CommandHandler("search", search))
application.add_handler(MessageHandler(filters.ALL & filters.ChatType.PRIVATE, handle_post))

if __name__ == "__main__":
    import asyncio
    from telegram.ext._asyncio import run_async
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        webhook_url=f"https://your-render-url.onrender.com/{API_TOKEN}"
    )
