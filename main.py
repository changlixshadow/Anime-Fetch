from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
import json
import os

# Configuration
API_TOKEN = "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc"  # Replace with your bot's API token
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"
USERS_FILE = "users.json"
GROUP_CHAT = "@sister_leveling"  # Group username or chat ID where requests get forwarded

for file_name in [POSTS_FILE, REQUESTS_FILE, USERS_FILE]:
    if not os.path.exists(file_name):
        with open(file_name, "w") as f:
            json.dump({} if file_name != REQUESTS_FILE else [], f)  # requests.json as list

# URLs for media and captions for start/about/help
START_URL = "https://telegra.ph/file/050a20dace942a60220c0-6afbc023e43fad29c7.jpg"
ABOUT_URL = "https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg"
HELP_URL = "https://telegra.ph/file/e6ec31fc792d072da2b7e-54e7c7d4c5651823b3.jpg"

START_CAPTION = (
    "✨ Welcome to Anime Garden! ✨\n\n"
    "Discover & Request your favorite Anime.\n"
    "Use the buttons below to explore more!\n\n"
    "Commands:\n"
    "/addpost - Admin only: Save an anime post with media, caption & buttons\n"
    "/animelist - List saved anime posts\n"
    "/search <name> - Search saved anime by name\n"
    "/requestanime <name> - Request an anime (will be forwarded to group)\n"
    "/viewrequests - View all anime requests\n"
    "/users - View how many users have started the bot (admin only)\n"
    "/broadcast - Broadcast a message to all users (admin only)\n"
    "/cancel - Cancel current operation\n"
)

ABOUT_CAPTION = (
    "📜 About Us\n\n"
    "Anime Garden is your one-stop destination for discovering and requesting Anime!"
)

HELP_CAPTION = (
    "⚙️ Help\n\n"
    "Commands:\n"
    "/addpost - Reply to a message containing anime media, caption & buttons to save it\n"
    "/animelist - List all saved anime posts\n"
    "/search <term> - Search anime posts by name\n"
    "/requestanime <name> - Request an anime (your request will be sent to the group)\n"
    "/viewrequests - View all user requests\n"
    "/users - View how many users have started the bot (admin only)\n"
    "/broadcast - Broadcast a message to all users (admin only)\n"
    "/cancel - Cancel any ongoing action\n\n"
    "Buttons in saved posts will be preserved and shown when displaying posts."
)

# States for ConversationHandler
WAITING_FOR_NAME = 0
WAITING_FOR_BROADCAST = 1

# Utility functions
def load_data(file_name):
    with open(file_name, "r") as f:
        data = json.load(f)
        if file_name == REQUESTS_FILE and not isinstance(data, list):
            data = []
        if file_name != REQUESTS_FILE and not isinstance(data, dict):
            data = {}
    return data

def save_data(file_name, data):
    with open(file_name, "w") as f:
        json.dump(data, f, indent=4)

# Save user info who starts the bot
async def save_user(update: Update):
    user = update.effective_user
    users = load_data(USERS_FILE)
    # Save username, first name, last name, keyed by user id
    users[str(user.id)] = {
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
    }
    save_data(USERS_FILE, users)

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await save_user(update)
    keyboard = [
        [
            InlineKeyboardButton("About 📜", callback_data="about"),
            InlineKeyboardButton("Help ⚙️", callback_data="help"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close")],
    ]
    await update.message.reply_photo(
        photo=START_URL,
        caption=START_CAPTION,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# Admin-only decorator
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        admin_ids = [5759232282]  # Put your Telegram user ID(s) here (int)
        user_id = update.effective_user.id
        if user_id not in admin_ids:
            await update.message.reply_text("You are not authorized to use this command.")
            return ConversationHandler.END
        return await func(update, context)
    return wrapper

# Helper: parse inline keyboard buttons from the message (if any)
def extract_buttons(message):
    if message.reply_markup and isinstance(message.reply_markup, InlineKeyboardMarkup):
        buttons = []
        for row in message.reply_markup.inline_keyboard:
            row_buttons = []
            for btn in row:
                btn_data = {"text": btn.text}
                if btn.callback_data:
                    btn_data["callback_data"] = btn.callback_data
                elif btn.url:
                    btn_data["url"] = btn.url
                row_buttons.append(btn_data)
            buttons.append(row_buttons)
        return buttons
    return None

# addpost command starts here
@admin_only
async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a message containing the anime details to save.")
        return ConversationHandler.END

    reply_msg = update.message.reply_to_message

    media_file_id = None
    media_type = None
    if reply_msg.photo:
        media_file_id = reply_msg.photo[-1].file_id
        media_type = "photo"
    elif reply_msg.document:
        media_file_id = reply_msg.document.file_id
        media_type = "document"
    else:
        await update.message.reply_text("No supported media found (photo/document).")
        return ConversationHandler.END

    caption = reply_msg.caption or ""

    buttons = extract_buttons(reply_msg)

    context.user_data["media"] = {"file_id": media_file_id, "type": media_type}
    context.user_data["caption"] = caption
    context.user_data["buttons"] = buttons

    await update.message.reply_text("What name should I save this post as? Reply with the name.")
    return WAITING_FOR_NAME

# Save post with media, caption, buttons
async def save_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_name = update.message.text.strip()
    if not post_name:
        await update.message.reply_text("Invalid name. Please try again.")
        return WAITING_FOR_NAME

    media = context.user_data.get("media")
    caption = context.user_data.get("caption")
    buttons = context.user_data.get("buttons")

    posts = load_data(POSTS_FILE)

    posts[post_name] = {
        "media": media,
        "caption": caption,
        "buttons": buttons,
    }
    save_data(POSTS_FILE, posts)

    await update.message.reply_text(f"Post saved as '{post_name}'!")
    return ConversationHandler.END

# Helper to recreate InlineKeyboardMarkup from stored buttons
def build_keyboard(buttons):
    if not buttons:
        return None
    keyboard = []
    for row in buttons:
        kb_row = []
        for btn in row:
            if "callback_data" in btn:
                kb_row.append(InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"]))
            elif "url" in btn:
                kb_row.append(InlineKeyboardButton(text=btn["text"], url=btn["url"]))
            else:
                kb_row.append(InlineKeyboardButton(text=btn["text"], callback_data="noop"))
        keyboard.append(kb_row)
    return InlineKeyboardMarkup(keyboard)

# Show list of saved anime posts
async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_data(POSTS_FILE)
    if not posts:
        await update.message.reply_text("No anime posts saved yet!")
        return

    response = "Saved Anime List:\n\n"
    for name in sorted(posts.keys()):
        response += f"- {name}\n"
    await update.message.reply_text(response)

# Search posts by name
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args).lower()
    if not query:
        await update.message.reply_text("Please provide a search term.")
        return

    posts = load_data(POSTS_FILE)
    results = [name for name in posts if query in name.lower()]

    if not results:
        await update.message.reply_text("No matches found!")
        return

    for name in results:
        post = posts[name]
        media = post["media"]
        caption = post["caption"]
        buttons = post.get("buttons")

        reply_markup = build_keyboard(buttons)

        if media["type"] == "photo":
            await update.message.reply_photo(
                photo=media["file_id"],
                caption=caption,
                reply_markup=reply_markup,
            )
        elif media["type"] == "document":
            await update.message.reply_document(
                document=media["file_id"],
                caption=caption,
                reply_markup=reply_markup,
            )

# Request anime command: save multiple requests as a list, forward to group
async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request_text = " ".join(context.args).strip()
    if not request_text:
        await update.message.reply_text("Please specify the anime you want to request.")
        return

    requests = load_data(REQUESTS_FILE)  # now a list

    user = update.effective_user
    user_name = user.username or user.first_name or "Unknown"

    # Append new request entry as a dict
    requests.append({
        "user_id": user.id,
        "username": user_name,
        "anime": request_text,
    })
    save_data(REQUESTS_FILE, requests)

    await update.message.reply_text(f"Your request for '{request_text}' has been recorded!")

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT,
            text=f"📢 New Anime Request from @{user_name}:\n{request_text}"
        )
    except Exception as e:
        print(f"Failed to send request to group: {e}")

# View all anime requests
@admin_only
async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requests = load_data(REQUESTS_FILE)
    if not requests:
        await update.message.reply_text("No requests found!")
        return

    response = "Anime Requests:\n\n"
    for req in requests:
        user_display = f"@{req['username']}" if req['username'] else "Unknown"
        response += f"{user_display}: {req['anime']}\n"
    await update.message.reply_text(response)

# Handle inline button queries for about/help/back/close
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    close_button = [InlineKeyboardButton("❌ Close", callback_data="close")]

    if query.data == "about":
        keyboard = [
            [InlineKeyboardButton("Back 🔙", callback_data="back"),
             InlineKeyboardButton("Help ⚙️", callback_data="help")],
            close_button
        ]
        await query.edit_message_media(
            media=InputMediaPhoto(ABOUT_URL, caption=ABOUT_CAPTION),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif query.data == "help":
        keyboard = [
            [InlineKeyboardButton("Back 🔙", callback_data="back"),
             InlineKeyboardButton("About 📜", callback_data="about")],
            close_button
        ]
        await query.edit_message_media(
            media=InputMediaPhoto(HELP_URL, caption=HELP_CAPTION),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif query.data == "back":
        keyboard = [
            [
                InlineKeyboardButton("About 📜", callback_data="about"),
                InlineKeyboardButton("Help ⚙️", callback_data="help"),
            ],
            close_button,
        ]
        await query.edit_message_media(
            media=InputMediaPhoto(START_URL, caption=START_CAPTION),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif query.data == "close":
        await query.delete_message()

# Cancel the conversation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operation canceled.")
    return ConversationHandler.END

# Admin-only command: show how many users have started the bot
@admin_only
async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_data(USERS_FILE)
    count = len(users)
    await update.message.reply_text(f"Total unique users who started the bot: {count}")

# Admin-only command: broadcast message to all users
@admin_only
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send me the message you want to broadcast to all users.")
    return WAITING_FOR_BROADCAST

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text
    users = load_data(USERS_FILE)

    sent_count = 0
    failed_count = 0

    for user_id_str in users.keys():
        try:
            await context.bot.send_message(chat_id=int(user_id_str), text=message_text)
            sent_count += 1
        except Exception:
            failed_count += 1

    await update.message.reply_text(f"Broadcast sent to {sent_count} users. Failed to send to {failed_count} users.")
    return ConversationHandler.END

def main():
    application = Application.builder().token(API_TOKEN).build()

    addpost_handler = ConversationHandler(
        entry_points=[CommandHandler("addpost", addpost)],
        states={
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_post)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    broadcast_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_start)],
        states={
            WAITING_FOR_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(addpost_handler)
    application.add_handler(broadcast_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("animelist", animelist))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("requestanime", requestanime))
    application.add_handler(CommandHandler("viewrequests", viewrequests))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
