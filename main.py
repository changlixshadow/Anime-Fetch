import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes
)
import logging

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# 🚨 IMPORTANT: Replace with your actual bot token and admin IDs
API_TOKEN = os.environ.get("API_TOKEN", "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc")  # Use environment variable for token
ADMIN_IDS = [5759232282]  # 🔁 Replace with your Telegram user IDs (can add multiple)

# Image URLs
START_IMG = "https://telegra.ph/file/050a20dace942a60220c0.jpg"
ABOUT_IMG = "https://telegra.ph/file/9d18345731db88fff4f8c.jpg"
HELP_IMG = "https://telegra.ph/file/e6ec31fc792d072da2b7e.jpg"

# File paths for data storage
POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

# --- File Handling Utilities ---
def ensure_file(file_path):
    """Ensures a JSON file exists and is initialized as an empty dictionary."""
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump({}, f)

def load_json(file_path):
    """Loads JSON data from a file."""
    ensure_file(file_path) # Ensure file exists before trying to load
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {file_path}. Initializing with empty dict.")
            return {} # Return empty dict if file is corrupted/empty

def save_json(file_path, data):
    """Saves data to a JSON file."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

# --- Inline Keyboard Markups ---
def start_markup():
    """Returns the inline keyboard for the /start command."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

def back_markup():
    """Returns the inline keyboard for 'back' navigation."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back"),
         InlineKeyboardButton("Help ⚙", callback_data="help")]
    ])

# --- Telegram Bot Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    caption = (
        "<b>✨ Welcome to Anime Garden ✨</b>\n\n"
        "Explore your favorite anime. Use the buttons below!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"  # 🔁 Update your channel username
        "<b>Backup:</b> @YourBackupChannel"  # 🔁 Update your backup channel username
    )
    await update.message.reply_photo(
        photo=START_IMG,
        caption=caption,
        parse_mode="HTML",
        reply_markup=start_markup()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /help command."""
    await update.message.reply_photo(
        photo=HELP_IMG,
        caption=(
            "<b>🛠 Help</b>\n\n"
            "/search &lt;name&gt; - 🔍 Search anime\n"
            "/animelist - 📑 List all available anime\n"
            "/requestanime &lt;name&gt; - 🙋 Request an anime\n\n"
            "<b>Admin Only Commands:</b>\n"
            "/addpost - ➕ Add a new anime post (send photo/video with caption and inline buttons)\n"
            "/viewrequests - 📬 View all pending anime requests"
        ),
        parse_mode="HTML"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline keyboard button presses."""
    query = update.callback_query
    await query.answer()  # Always answer the callback query

    data = query.data

    if data == "about":
        caption = (
            "<b>📜 About Us</b>\n\n"
            "Sharing new anime daily with our community!\n\n"
            "📺 <a href='https://t.me/YourMainChannel'>Main Channel</a>\n" # 🔁 Update your channel link
            "🛡 <a href='https://t.me/YourBackupChannel'>Backup Channel</a>\n" # 🔁 Update your channel link
            "🔞 <a href='https://t.me/YourEcchiChannel'>NSFW Channel</a>" # 🔁 Update your channel link
        )
        await query.message.edit_media(
            InputMediaPhoto(ABOUT_IMG, caption=caption, parse_mode="HTML"),
            reply_markup=back_markup()
        )
    elif data == "help":
        # Note: This is similar to /help but updates the existing message
        await query.message.edit_media(
            InputMediaPhoto(HELP_IMG, caption=(
                "<b>🛠 Help Menu</b>\n\n"
                "/search &lt;name&gt;\n"
                "/requestanime &lt;name&gt;\n"
                "/animelist\n"
                "/addpost (admin only)"
            ), parse_mode="HTML"),
            reply_markup=back_markup()
        )
    elif data == "back":
        caption = (
            "<b>✨ Welcome to Anime Garden ✨</b>\n\n"
            "<b>Channel:</b> @YourMainChannel\n" # 🔁 Update your channel username
            "<b>Backup:</b> @YourBackupChannel" # 🔁 Update your channel username
        )
        await query.message.edit_media(
            InputMediaPhoto(START_IMG, caption=caption, parse_mode="HTML"),
            reply_markup=start_markup()
        )
    elif data == "close":
        await query.message.delete()

async def addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to add a new anime post.
    The message must contain a photo or video and optional caption and inline buttons.
    """
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return

    if not (update.message.photo or update.message.video):
        await update.message.reply_text(
            "Please send a photo or video with the `/addpost` command, "
            "along with a caption and any desired inline buttons."
        )
        return

    media_type = "photo" if update.message.photo else "video"
    file_id = update.message.photo[-1].file_id if media_type == "photo" else update.message.video.file_id
    caption = update.message.caption or ""

    # Parse inline buttons for storage
    parsed_buttons = []
    if update.message.reply_markup and update.message.reply_markup.inline_keyboard:
        for row in update.message.reply_markup.inline_keyboard:
            parsed_row = []
            for button in row:
                if button.url: # Only save URL buttons for simplicity
                    parsed_row.append({"text": button.text, "url": button.url})
            if parsed_row: # Only add row if it contains valid buttons
                parsed_buttons.append(parsed_row)

    posts = load_json(POSTS_FILE)
    # Use a simple incrementing ID for posts
    next_id = str(max([int(k) for k in posts.keys()]) + 1) if posts else "1"
    
    posts[next_id] = {
        "media_type": media_type,
        "file_id": file_id,
        "caption": caption,
        "buttons": parsed_buttons
    }
    save_json(POSTS_FILE, posts)
    await update.message.reply_text("✅ Post saved successfully!")
    logging.info(f"Admin {user_id} added a new post (ID: {next_id}).")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Searches for anime posts based on a query in the caption."""
    if not context.args:
        await update.message.reply_text("Usage: `/search <name>`")
        return

    query = ' '.join(context.args).lower()
    posts = load_json(POSTS_FILE)
    
    found_posts_count = 0
    for post_id, post in posts.items():
        if query in post["caption"].lower():
            found_posts_count += 1
            markup = None
            if post.get("buttons"):
                try:
                    # Reconstruct InlineKeyboardMarkup from saved data
                    buttons_list = []
                    for row in post["buttons"]:
                        row_buttons = []
                        for b in row:
                            row_buttons.append(InlineKeyboardButton(b["text"], url=b["url"]))
                        buttons_list.append(row_buttons)
                    markup = InlineKeyboardMarkup(buttons_list)
                except Exception as e:
                    logging.error(f"Error reconstructing markup for post {post_id}: {e}")
                    markup = None # Fallback if button data is malformed

            if post["media_type"] == "photo":
                await update.message.reply_photo(
                    post["file_id"], caption=post["caption"], reply_markup=markup, parse_mode="HTML"
                )
            else: # media_type == "video"
                await update.message.reply_video(
                    post["file_id"], caption=post["caption"], reply_markup=markup, parse_mode="HTML"
                )
            # You can decide if you want to send only the first match or all matches
            # If you want only the first, uncomment the 'return' below:
            # return
    
    if found_posts_count == 0:
        await update.message.reply_text("❌ No matching anime found.")
    else:
        await update.message.reply_text(f"✅ Found {found_posts_count} matching anime posts.")


async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows users to request an anime."""
    name = ' '.join(context.args).strip()
    if not name:
        await update.message.reply_text("Usage: `/requestanime <name of anime>`")
        return

    requests = load_json(REQUESTS_FILE)
    user_id_str = str(update.effective_user.id)
    user_name = update.effective_user.first_name or f"User {user_id_str}" # Get user's first name

    if user_id_str not in requests:
        requests[user_id_str] = []
    
    requests[user_id_str].append({"anime": name, "timestamp": update.message.date.isoformat(), "user_name": user_name})
    save_json(REQUESTS_FILE, requests)

    await update.message.reply_text("✅ Your request was sent successfully!")
    logging.info(f"User {user_id_str} ({user_name}) requested: {name}")

    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📥 New Anime Request from <b>{user_name}</b> (ID: <code>{user_id_str}</code>):\n\n"
                f"Anime: <b>{name}</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            logging.error(f"Failed to send request notification to admin {admin_id}: {e}")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to view all pending anime requests."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return
    
    requests = load_json(REQUESTS_FILE)
    
    if not requests:
        await update.message.reply_text("📬 No anime requests have been made yet.")
        return

    response_lines = ["<b>📬 Current Anime Requests:</b>"]
    for user_id, user_requests in requests.items():
        if user_requests: # Only process if there are actual requests for this user
            # Get user_name from the first request if available, otherwise use ID
            user_name = user_requests[0].get("user_name", f"User {user_id}")
            response_lines.append(f"\n<b>User: {user_name}</b> (ID: <code>{user_id}</code>)")
            for i, req in enumerate(user_requests):
                anime_name = req.get("anime", "N/A")
                timestamp = req.get("timestamp", "N/A")
                response_lines.append(f"  {i+1}. <i>{anime_name}</i> (Requested on {timestamp[:10]})") # Just date
    
    # Split message if it's too long
    full_text = "\n".join(response_lines)
    if len(full_text) > 4096: # Telegram message limit
        # Simple splitting: you might want more sophisticated logic for very long lists
        chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await update.message.reply_text(full_text, parse_mode="HTML")

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all available anime posts."""
    posts = load_json(POSTS_FILE)
    
    if not posts:
        await update.message.reply_text("📑 No anime posts available yet. Admins can add them using /addpost.")
        return

    # Sort posts by key (which implies creation order if keys are numeric IDs)
    sorted_posts_items = sorted(posts.items(), key=lambda item: int(item[0]))

    response_lines = ["<b>📑 Available Anime Posts:</b>"]
    for i, (post_id, p) in enumerate(sorted_posts_items):
        caption_preview = p['caption'].split('\n')[0] # Take only the first line of caption
        if len(caption_preview) > 50: # Limit preview length
            caption_preview = caption_preview[:47] + "..."
        
        response_lines.append(f"{i+1}. <i>{caption_preview}</i> (ID: <code>{post_id}</code>)")
    
    full_text = "\n".join(response_lines)

    if len(full_text) > 4096:
        # If the list is very long, send it in chunks
        chunks = [full_text[i:i+4000] for i in range(0, len(full_text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode="HTML")
    else:
        await update.message.reply_text(full_text, parse_mode="HTML")


# --- Main Bot Runner ---
def run_bot():
    """Initializes and runs the Telegram bot."""
    # Ensure data files exist before starting
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    application = Application.builder().token(API_TOKEN).build()

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addpost", addpost))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("requestanime", requestanime))
    application.add_handler(CommandHandler("viewrequests", viewrequests))
    application.add_handler(CommandHandler("animelist", animelist))

    # Callback Query Handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_handler))

    # Message Handler for /addpost (to catch media) - if you want to handle general media
    # For /addpost, it's better to process the message *after* the command.
    # The current `addpost` function already expects `update.message.photo` or `update.message.video`.
    # If you want a catch-all for unknown commands:
    # application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logging.info("✅ Bot is starting polling...")
    application.run_polling(poll_interval=3, timeout=30) # Add poll_interval and timeout for robustness

if __name__ == "__main__":
    run_bot()
