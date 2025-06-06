import os
import json
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"  # 🔁 Replace with your bot token
ADMIN_IDS = [5759232282]       # 🔁 Replace with your Telegram user ID

START_IMG = "https://telegra.ph/file/050a20dace942a60220c0.jpg"
ABOUT_IMG = "https://telegra.ph/file/9d18345731db88fff4f8c.jpg"
HELP_IMG = "https://telegra.ph/file/e6ec31fc792d072da2b7e.jpg"

POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

app = Flask(__name__)

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

# -- BUTTONS --
def start_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

def back_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back"),
         InlineKeyboardButton("Help ⚙", callback_data="help")]
    ])

# -- COMMANDS --

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>✨ Welcome to Anime Garden ✨</b>\n\n"
        "Explore your favorite anime. Use the buttons below!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel"
    )
    await update.message.reply_photo(photo=START_IMG, caption=caption,
                                     parse_mode="HTML", reply_markup=start_markup())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(photo=HELP_IMG, caption=(
        "<b>🛠 Help</b>\n\n"
        "/search <name> - 🔍 Search anime\n"
        "/animelist - 📑 List all\n"
        "/requestanime <name> - 🙋 Request anime\n\n"
        "<b>Admin Only</b>\n"
        "/addpost - ➕ Add post\n"
        "/viewrequests - 📬 View requests"
    ), parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "about":
        caption = (
            "<b>📜 About Us</b>\n\n"
            "Sharing new anime daily!\n\n"
            "📺 @YourMainChannel\n🛡 @YourBackupChannel\n🌶 NSFW: @YourEcchiChannel"
        )
        await query.message.edit_media(InputMediaPhoto(ABOUT_IMG, caption=caption, parse_mode="HTML"), reply_markup=back_markup())
    elif data == "help":
        await query.message.edit_media(InputMediaPhoto(HELP_IMG, caption=(
            "<b>🛠 Help Menu</b>\n\n"
            "/search <name>\n"
            "/requestanime <name>\n"
            "/animelist\n"
            "/addpost (admin)"
        ), parse_mode="HTML"), reply_markup=back_markup())
    elif data == "back":
        await query.message.edit_media(InputMediaPhoto(START_IMG, caption=(
            "<b>✨ Welcome to Anime Garden ✨</b>\n\n<b>Channel:</b> @YourMainChannel\n<b>Backup:</b> @YourBackupChannel"
        ), parse_mode="HTML"), reply_markup=start_markup())
    elif data == "close":
        await query.message.delete()

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    if not (update.message.photo or update.message.video):
        return

    media_type = "photo" if update.message.photo else "video"
    file_id = update.message.photo[-1].file_id if media_type == "photo" else update.message.video.file_id
    caption = update.message.caption or ""
    buttons = update.message.reply_markup.inline_keyboard if update.message.reply_markup else []
    parsed_buttons = [[{"text": b.text, "url": b.url} for b in row] for row in buttons]

    posts = load_json(POSTS_FILE)
    posts[str(len(posts)+1)] = {
        "media_type": media_type,
        "file_id": file_id,
        "caption": caption,
        "buttons": parsed_buttons
    }
    save_json(POSTS_FILE, posts)
    await update.message.reply_text("✅ Post saved!")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args).lower()
    posts = load_json(POSTS_FILE)
    for post in posts.values():
        if query in post["caption"].lower():
            markup = InlineKeyboardMarkup([
                [InlineKeyboardButton(b["text"], url=b["url"]) for b in row] for row in post.get("buttons", [])
            ])
            if post["media_type"] == "photo":
                await update.message.reply_photo(post["file_id"], caption=post["caption"], reply_markup=markup)
            else:
                await update.message.reply_video(post["file_id"], caption=post["caption"], reply_markup=markup)
            return
    await update.message.reply_text("❌ No matching anime found.")

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        return await update.message.reply_text("Usage: /requestanime <name>")
    requests = load_json(REQUESTS_FILE)
    user = str(update.effective_user.id)
    requests[user] = requests.get(user, []) + [name]
    save_json(REQUESTS_FILE, requests)
    await update.message.reply_text("✅ Your request was sent!")
    for admin in ADMIN_IDS:
        await context.bot.send_message(admin, f"📥 Request from {update.effective_user.first_name}: {name}")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    requests = load_json(REQUESTS_FILE)
    text = "\n".join([f"{k}: {', '.join(v)}" for k, v in requests.items()])
    await update.message.reply_text(text or "No requests yet.")

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    lines = [f"{i+1}. {p['caption'][:30]}..." for i, p in enumerate(posts.values())]
    await update.message.reply_text("\n".join(lines) or "No posts yet.")

# -- RUN BOT --
def run_bot():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    app_ = Application.builder().token(API_TOKEN).build()

    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("addpost", addpost))
    app_.add_handler(CommandHandler("search", search))
    app_.add_handler(CommandHandler("requestanime", requestanime))
    app_.add_handler(CommandHandler("viewrequests", viewrequests))
    app_.add_handler(CommandHandler("animelist", animelist))
    app_.add_handler(CallbackQueryHandler(button_handler))

    print("✅ Bot is running...")
    app_.run_polling()

if __name__ == "__main__":
    run_bot()
