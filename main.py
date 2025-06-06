import os
import json
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"
ADMIN_IDS = [5759232282]
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

START_IMAGE = "https://telegra.ph/file/050a20dace942a60220c0-6afbc023e43fad29c7.jpg"
ABOUT_IMAGE = "https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg"
HELP_IMAGE = "https://telegra.ph/file/e6ec31fc792d072da2b7e-54e7c7d4c5651823b3.jpg"

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

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

def start_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙️", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

def back_buttons():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "✨ <b>Welcome to Anime Garden!</b> ✨\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel"
    )
    await update.message.reply_photo(
        photo=START_IMAGE, caption=caption,
        parse_mode='HTML', reply_markup=start_buttons()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "about":
        caption = (
            "<b>📜 About This Bot</b>\n\n"
            "Your personal Anime Finder 🤖\n"
            "Explore, Request & Enjoy Anime effortlessly!\n\n"
            "<a href='https://t.me/YourMainChannel'>📺 Main Channel</a>\n"
            "<a href='https://t.me/YourBackupChannel'>🛰 Backup Channel</a>\n"
            "<a href='https://t.me/YourSupportGroup'>💬 Support Group</a>"
        )
        await query.message.edit_media(
            media={"type": "photo", "media": ABOUT_IMAGE},
            reply_markup=back_buttons()
        )
        await query.message.edit_caption(caption=caption, parse_mode='HTML')

    elif query.data == "help":
        caption = (
            "⚙️ <b>Help Panel</b>\n\n"
            "🔍 /search <name> - Find Anime\n"
            "📚 /animelist - Show All\n"
            "📝 /requestanime <name> - Request Upload\n\n"
            "👑 Admin Commands:\n"
            "➕ /addpost\n📥 /viewrequests"
        )
        await query.message.edit_media(
            media={"type": "photo", "media": HELP_IMAGE},
            reply_markup=back_buttons()
        )
        await query.message.edit_caption(caption=caption, parse_mode='HTML')

    elif query.data == "back":
        await query.message.edit_media(
            media={"type": "photo", "media": START_IMAGE},
            reply_markup=start_buttons()
        )
        await query.message.edit_caption(
            caption=(
                "✨ <b>Welcome to Anime Garden!</b> ✨\n\n"
                "Discover & Request your favorite Anime.\n\n"
                "<b>Channel:</b> @YourMainChannel\n"
                "<b>Backup:</b> @YourBackupChannel"
            ),
            parse_mode='HTML'
        )

    elif query.data == "close":
        await query.message.delete()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(HELP_IMAGE, caption="⚙️ Use /start and tap Help ⚙️", parse_mode='HTML')

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Unknown command. Use /help to know available commands.")

async def delete_unwanted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not update.message.photo and not update.message.video:
        return
    media_type = 'photo' if update.message.photo else 'video'
    file_id = update.message.photo[-1].file_id if media_type == 'photo' else update.message.video.file_id
    caption = update.message.caption or ""
    post_id = str(len(load_json(POSTS_FILE)) + 1)
    post_data = load_json(POSTS_FILE)
    post_data[post_id] = {
        "media_type": media_type,
        "file_id": file_id,
        "caption": caption
    }
    save_json(POSTS_FILE, post_data)
    await update.message.reply_text("✅ Post saved!")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    query = ' '.join(context.args).lower()
    found = False
    for post in posts.values():
        if query in post["caption"].lower():
            if post["media_type"] == "photo":
                await update.message.reply_photo(post["file_id"], caption=post["caption"])
            else:
                await update.message.reply_video(post["file_id"], caption=post["caption"])
            found = True
    if not found:
        await update.message.reply_text("❌ No anime found!")

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        return await update.message.reply_text("📝 Usage: /requestanime <anime name>")
    requests = load_json(REQUESTS_FILE)
    uid = str(update.effective_user.id)
    requests[uid] = requests.get(uid, []) + [name]
    save_json(REQUESTS_FILE, requests)
    await update.message.reply_text("📥 Request sent to admin!")
    for admin in ADMIN_IDS:
        await context.bot.send_message(admin, f"📩 Request from {uid}: {name}")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    requests = load_json(REQUESTS_FILE)
    if uid in map(str, ADMIN_IDS):
        msg = "\n".join([f"{k}: {', '.join(v)}" for k, v in requests.items()])
    else:
        msg = "\n".join(requests.get(uid, ["No requests found."]))
    await update.message.reply_text(msg)

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
    per_page = 5
    keys = list(posts.keys())
    total_pages = (len(keys) + per_page - 1) // per_page
    start, end = (page - 1) * per_page, page * per_page
    lines = [f"{i+1}. {posts[k]['caption'][:30]}..." for i, k in enumerate(keys[start:end])]
    buttons = []
    if page > 1:
        buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if page < total_pages:
        buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page+1}"))
    markup = InlineKeyboardMarkup([buttons]) if buttons else None
    await update.message.reply_text("\n".join(lines), reply_markup=markup)

async def page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    context.args = [str(page)]
    update.message = query.message
    await animelist(update, context)

def run():
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)
    app_ = Application.builder().token(API_TOKEN).build()

    app_.add_handler(CommandHandler("start", start))
    app_.add_handler(CallbackQueryHandler(button_handler, pattern="^(about|help|back|close)$"))
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("addpost", addpost))
    app_.add_handler(CommandHandler("search", search))
    app_.add_handler(CommandHandler("requestanime", requestanime))
    app_.add_handler(CommandHandler("viewrequests", viewrequests))
    app_.add_handler(CommandHandler("animelist", animelist))
    app_.add_handler(CallbackQueryHandler(page_callback, pattern=r"^page:"))
    app_.add_handler(MessageHandler(filters.COMMAND, unknown))
    app_.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_unwanted))

    print("Bot running...")
    app_.run_polling()

if __name__ == '__main__':
    run()
