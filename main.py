from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import json
import os

API_TOKEN = "8006836827:AAF7YXTukf_5tU4mnNKzKxIBbQnq08yxrHM"
POSTS_FILE = "posts.json"
ADMIN_ID = 5759232282

WAITING_FOR_MEDIA, WAITING_FOR_NAME = range(2)

def ensure_posts_file():
    if not os.path.exists(POSTS_FILE):
        with open(POSTS_FILE, "w") as f:
            json.dump({}, f)

def save_post(name, data):
    ensure_posts_file()
    with open(POSTS_FILE, "r") as f:
        posts = json.load(f)
    posts[name] = data
    with open(POSTS_FILE, "w") as f:
        json.dump(posts, f, indent=4)

def load_posts():
    ensure_posts_file()
    with open(POSTS_FILE, "r") as f:
        return json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to the Anime Bot! 🚀\n\n"
        "Commands:\n"
        "/addpost - Add a new anime post (Admin only)\n"
        "/search <name> - Search for an anime\n"
        "/animelist - View the list of saved anime\n"
    )

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("You are not authorized to use this command.")
        return ConversationHandler.END

    await update.message.reply_text("Please send the photo or video you want to save with optional caption and buttons.")
    return WAITING_FOR_MEDIA

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
        await update.message.reply_text("Please send a photo or video.")
        return WAITING_FOR_MEDIA

    caption = update.message.caption or ""

    buttons = []
    if update.message.reply_markup and isinstance(update.message.reply_markup, InlineKeyboardMarkup):
        for row in update.message.reply_markup.inline_keyboard:
            buttons.append([{"text": button.text, "url": button.url} for button in row])

    context.user_data["media"] = media
    context.user_data["caption"] = caption
    context.user_data["type"] = media_type
    context.user_data["buttons"] = buttons

    await update.message.reply_text("What name should I save this as? Reply with the name.")
    return WAITING_FOR_NAME

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    media = context.user_data.get("media")
    caption = context.user_data.get("caption")
    media_type = context.user_data.get("type")
    buttons = context.user_data.get("buttons")

    if not media:
        await update.message.reply_text("No media found to save. Please start again with /addpost.")
        return ConversationHandler.END

    data = {"media": media, "caption": caption, "type": media_type, "buttons": buttons}
    save_post(name, data)

    await update.message.reply_text(f"Post saved as '{name}'!")
    return ConversationHandler.END

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_posts()
    if not posts:
        await update.message.reply_text("No anime saved yet.")
        return

    sorted_posts = sorted(posts.keys())
    message = "Saved Anime List:\n\n"
    current_letter = None

    for name in sorted_posts:
        first_letter = name[0].upper()
        if first_letter != current_letter:
            current_letter = first_letter
            message += f"\n*{current_letter}*\n"
        message += f" - {name}\n"

    await update.message.reply_text(message, parse_mode="Markdown")

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text("Please provide a name to search.")
        return

    name = " ".join(context.args)
    posts = load_posts()

    if name in posts:
        post = posts[name]

        button_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton(text=btn["text"], url=btn["url"]) for btn in row] for row in post.get("buttons", [])]
        )

        if post["type"] == "photo":
            await update.message.reply_photo(
                photo=post["media"], caption=post["caption"], reply_markup=button_markup
            )
        else:
            await update.message.reply_video(
                video=post["media"], caption=post["caption"], reply_markup=button_markup
            )
    else:
        await update.message.reply_text("No post found with that name.")

async def handle_unrecognized(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only respond in private chats (ignore group chat random messages)
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Unrecognized command. Use:\n"
            "/search <name> to find an anime\n"
            "/animelist to see the list of saved anime."
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Action canceled.")
    return ConversationHandler.END

def main():
    ensure_posts_file()

    application = Application.builder().token(API_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addpost", addpost, filters=filters.ChatType.PRIVATE | filters.ChatType.GROUP)],
        states={
            WAITING_FOR_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, receive_media)],
            WAITING_FOR_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    # Add handlers for commands, allow both private and group commands
    application.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE | filters.ChatType.GROUP))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("animelist", animelist, filters=filters.ChatType.PRIVATE | filters.ChatType.GROUP))
    application.add_handler(CommandHandler("search", search, filters=filters.ChatType.PRIVATE | filters.ChatType.GROUP))

    # For unrecognized commands, reply only in private chat to avoid spam in groups
    application.add_handler(MessageHandler(filters.ALL, handle_unrecognized, block=False))

    print("Bot is running 🚀")
    application.run_polling()

if __name__ == "__main__":
    main()
