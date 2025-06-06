import os
import json
from flask import Flask
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode

API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"  # Replace with your bot token
ADMIN_IDS = [5759232282]  # Replace with admin Telegram IDs
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

def back_help_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back"),
         InlineKeyboardButton("⚙️ Help", callback_data="help")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "✨ <b>Welcome to Anime Garden!</b> ✨\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel\n"
    )
    await update.message.reply_photo(photo=START_IMAGE, caption=caption,
                                     parse_mode='HTML', reply_markup=start_buttons())

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "about":
        caption = (
            "<b>ℹ About</b>\n\n"
            "We share new anime episodes daily!\n"
            "\n<b>Main:</b> @YourMainChannel\n"
            "<b>Backup:</b> @YourBackupChannel\n"
            "<b>NSFW:</b> @YourEcchiChannel\n"
        )
        await query.message.edit_media(InputMediaPhoto(ABOUT_IMAGE, caption=caption, parse_mode='HTML'),
                                       reply_markup=back_help_buttons())
    elif query.data == "help":
        caption = (
            "<b>⚙ Help Guide</b>\n\n"
            "▶ /search <name> - Find anime\n"
            "▶ /animelist - Show all posts\n"
            "▶ /requestanime <name> - Request new anime\n\n"
            "<b>Admins Only:</b>\n"
            "✅ /addpost - Save post with buttons\n"
            "✅ /viewrequests - See user requests\n"
        )
        await query.message.edit_media(InputMediaPhoto(HELP_IMAGE, caption=caption, parse_mode='HTML'),
                                       reply_markup=back_help_buttons())
    elif query.data == "back":
        await query.message.edit_media(InputMediaPhoto(START_IMAGE, caption=
            "✨ <b>Welcome to Anime Garden!</b> ✨\n\nDiscover & Request your favorite Anime.\n\n<b>Channel:</b> @YourMainChannel\n<b>Backup:</b> @YourBackupChannel",
            parse_mode='HTML'), reply_markup=start_buttons())
    elif query.data == "close":
        await query.message.delete()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(photo=HELP_IMAGE, caption=(
        "<b>⚙ Help Guide</b>\n\n"
        "▶ /search <name>\n▶ /animelist\n▶ /requestanime <name>\n\n<b>Admins:</b>\n✅ /addpost\n✅ /viewrequests"
    ), parse_mode='HTML')

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help")

async def delete_unwanted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.delete()
    except:
        pass

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not (update.message.photo or update.message.video):
        return
    media_type = 'photo' if update.message.photo else 'video'
    file_id = update.message.photo[-1].file_id if media_type == 'photo' else update.message.video.file_id
    caption = update.message.caption or ""
    markup = update.message.reply_markup
    button_data = []
    if markup:
        for row in markup.inline_keyboard:
            button_data.append([{"text": btn.text, "url": btn.url} for btn in row])
    post_id = str(len(load_json(POSTS_FILE)) + 1)
    post_data = load_json(POSTS_FILE)
    post_data[post_id] = {
        "media_type": media_type,
        "file_id": file_id,
        "caption": caption,
        "buttons": button_data
    }
    save_json(POSTS_FILE, post_data)
    await update.message.reply_text("✅ Post saved!")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    query = ' '.join(context.args).lower()
    for post in posts.values():
        if query in post["caption"].lower():
            markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton(btn["text"], url=btn["url"]) for btn in row] for row in post.get("buttons", [])]
            )
            if post["media_type"] == "photo":
                await update.message.reply_photo(post["file_id"], caption=post["caption"], reply_markup=markup)
            else:
                await update.message.reply_video(post["file_id"], caption=post["caption"], reply_markup=markup)
            return
    await update.message.reply_text("❌ No matching anime found.")

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        return await update.message.reply_text("❗ Usage: /requestanime <anime name>")
    requests = load_json(REQUESTS_FILE)
    user_id = str(update.effective_user.id)
    requests[user_id] = requests.get(user_id, []) + [name]
    save_json(REQUESTS_FILE, requests)
    await update.message.reply_text("✅ Your request has been sent!")
    for admin in ADMIN_IDS:
        await context.bot.send_message(admin, f"📥 Request from {update.effective_user.first_name}: {name}")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("⛔ Not allowed")
    requests = load_json(REQUESTS_FILE)
    msg = "\n".join([f"{uid}: {', '.join(reqs)}" for uid, reqs in requests.items()])
    await update.message.reply_text(msg or "No requests")

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 1
    per_page = 5
    keys = list(posts.keys())
    total_pages = (len(keys) + per_page - 1) // per_page
    start, end = (page - 1) * per_page, page * per_page
    media = [f"{i + 1}. {posts[k]['caption'][:30]}..." for i, k in enumerate(keys[start:end])]
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page - 1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page + 1}"))
    markup = InlineKeyboardMarkup([nav_buttons]) if nav_buttons else None
    await update.message.reply_text("\n".join(media), reply_markup=markup)

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
    app_.add_handler(CommandHandler("help", help_command))
    app_.add_handler(CommandHandler("addpost", addpost))
    app_.add_handler(CommandHandler("search", search))
    app_.add_handler(CommandHandler("requestanime", requestanime))
    app_.add_handler(CommandHandler("viewrequests", viewrequests))
    app_.add_handler(CommandHandler("animelist", animelist))
    app_.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(about|help|back|close)$"))
    app_.add_handler(CallbackQueryHandler(page_callback, pattern=r"^page:"))
    app_.add_handler(MessageHandler(filters.COMMAND, unknown))
    app_.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_unwanted))
    print("Bot running...")
    app_.run_polling()

if __name__ == '__main__':
    run()
