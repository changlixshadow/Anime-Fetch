# main.py

import logging
import json
import os
import re
from functools import wraps

import telegram # Import the entire telegram module
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Your actual bot token from BotFather
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc")
# Your Telegram user ID(s) who will be admins
ADMIN_IDS = [int(admin_id) for admin_id in os.environ.get("ADMIN_IDS", "5759232282").split(',') if admin_id]
# Your admin group chat ID where requests will be forwarded
ADMIN_GROUP_ID = int(os.environ.get("ADMIN_GROUP_ID", "-1002328544177"))
# Your channel link (REMINDER: Please replace this with your actual channel link!)
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/your_anime_channel_link")
# Your about image URL
ABOUT_IMAGE_URL = os.environ.get("ABOUT_IMAGE_URL", "https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg")
# Your start image URL
START_IMAGE_URL = os.environ.get("START_IMAGE_URL", "https://telegra.ph/file/050a20dace942a60220c0-6afbc023e43fad29c7.jpg")
# Your help image URL
HELP_IMAGE_URL = os.environ.get("HELP_IMAGE_URL", "https://telegra.ph/file/e6ec31fc792d072da2b7e-54e7c7d4c5651823b3.jpg")


# --- File Paths ---
POSTS_FILE = 'posts.json'
REQUESTS_FILE = 'requests.json'
USERS_FILE = 'users.json' # To store user IDs for broadcast

# --- Global Data Stores ---
posts_data = {}
requests_data = {}
users_data = {}

# --- Helper Functions for Data Persistence ---
def load_data(file_path):
    """Loads data from a JSON file."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Error decoding JSON from {file_path}. Returning empty dict.")
                return {}
    return {}

def save_data(data, file_path):
    """Saves data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def init_data_stores():
    """Initializes global data stores from files."""
    global posts_data, requests_data, users_data
    posts_data = load_data(POSTS_FILE)
    requests_data = load_data(REQUESTS_FILE)
    users_data = load_data(USERS_FILE)

# --- Decorators ---
def restricted(func):
    """Decorator to restrict access to admin users."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ You are not authorized to use this command. Only admins can use it."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# --- Keyboard Markups ---
def get_start_keyboard():
    """Returns the keyboard for the /start command."""
    keyboard = [
        [
            InlineKeyboardButton("ℹ️ About", callback_data="about_btn"),
            InlineKeyboardButton("❓ Help", callback_data="help_btn"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close_btn")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_about_help_keyboard():
    """Returns the keyboard for About/Help sections."""
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Back", callback_data="back_to_start_btn"),
            InlineKeyboardButton("❓ Help", callback_data="help_btn"),
        ],
        [InlineKeyboardButton("❌ Close", callback_data="close_btn")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_animelist_pagination_keyboard(current_page, total_pages):
    """Returns pagination keyboard for /Animelist."""
    keyboard = []
    row = []
    if current_page > 0:
        row.append(InlineKeyboardButton("⬅️ Prev Page", callback_data=f"animelist_prev_{current_page}"))
    if current_page < total_pages - 1:
        row.append(InlineKeyboardButton("➡️ Next Page", callback_data=f"animelist_next_{current_page}"))
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close_btn")])
    return InlineKeyboardMarkup(keyboard)


# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with an image and buttons."""
    user = update.effective_user
    logger.info(f"User {user.id} started the bot.")

    # Add user to users_data for broadcast
    if str(user.id) not in users_data:
        users_data[str(user.id)] = True
        save_data(users_data, USERS_FILE)

    caption = (
        f"👋 Hello {user.first_name}! Welcome to your Anime Channel Bot.✨\n\n"
        "You can find your favorite anime here, check new releases and much more.\n\n"
        "Use the buttons below or these commands:\n\n"
        "✨ `/search <anime name>` - Search for an anime\n"
        "📋 `/Animelist` - See the list of available anime\n"
        "📝 `/requestanime <anime name>` - Request a new anime\n"
        "❓ `/help` - Get all commands and information"
    )
    
    await update.message.reply_photo(
        photo=START_IMAGE_URL,
        caption=caption,
        reply_markup=get_start_keyboard(),
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a help message with available commands."""
    help_text = (
        "📚 **Help Menu**\n\n"
        "Here are some commands you can use:\n\n"
        "✨ `/start` - Restart the bot and see the main menu.\n"
        "❓ `/help` - See this help message.\n"
        "🔍 `/search <anime name>` - Search for your favorite anime by name.\n"
        "📋 `/Animelist` - View the complete list of all anime available on the channel.\n"
        "📝 `/requestanime <anime name>` - Request an anime that is not yet available.\n"
        "👀 `/viewrequest` - See your past anime requests.\n\n"
        "**Admin Commands (for Admins only):**\n"
        "➕ `/addpost` - Add a new anime post.\n"
        "📢 `/broadcast <message>` - Send a message to all bot users.\n"
        "🔔 `/notifyrequest <username> <message>` - Notify a user about the availability of their requested anime.\n\n"
        "If you need further assistance, please visit our [Main Channel]("
        + CHANNEL_LINK
        + ")."
    )
    
    # Check if the command came from a message or a callback query
    if update.callback_query:
        await update.callback_query.message.edit_media(
            media=telegram.InputMediaPhoto(media=HELP_IMAGE_URL, caption=help_text),
            reply_markup=get_about_help_keyboard(),
            parse_mode="Markdown"
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_photo(
            photo=HELP_IMAGE_URL,
            caption=help_text,
            reply_markup=get_about_help_keyboard(),
            parse_mode="Markdown"
        )

@restricted
async def addpost_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Starts the process of adding a new post."""
    await update.message.reply_text("📝 Please enter the name for this post by which it will be searchable:")
    context.user_data['state'] = 'waiting_for_post_name'

async def receive_post_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receives the post name and asks for the media."""
    if context.user_data.get('state') == 'waiting_for_post_name':
        post_name = update.message.text.strip()
        if not post_name:
            await update.message.reply_text("❌ Post name cannot be empty. Please enter a valid name:")
            return

        context.user_data['new_post_name'] = post_name
        context.user_data['state'] = 'waiting_for_post_media'
        await update.message.reply_text(
            f"✅ Post name '{post_name}' saved. \n"
            "🖼️ Now, please send the media (photo/video) with its caption you want to post. "
            "Note: Telegram's API does not allow bots to extract inline buttons from forwarded messages. "
            "You will need to manually add buttons in the next step."
        )
    else:
        # This message is not a post name, handle it as a regular message or ignore
        pass # The general message handler will catch regular text messages

@restricted
async def handle_post_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receives the media, caption, and asks for button details."""
    if context.user_data.get('state') == 'waiting_for_post_media':
        post_name = context.user_data.get('new_post_name')

        if not post_name:
            await update.message.reply_text("❌ Error: Post name not found. Please restart with /addpost.")
            context.user_data.pop('state', None)
            context.user_data.pop('new_post_name', None)
            return

        file_id = None
        media_type = None
        if update.message.photo:
            file_id = update.message.photo[-1].file_id # Get the largest photo
            media_type = 'photo'
        elif update.message.video:
            file_id = update.message.video.file_id
            media_type = 'video'
        else:
            await update.message.reply_text("❌ Please send a photo or video. Text or other media types are not supported.")
            return

        caption_text = update.message.caption if update.message.caption else ""

        # Store temporary post data
        context.user_data['temp_post'] = {
            'file_id': file_id,
            'media_type': media_type,
            'caption': caption_text,
            'buttons': [] # This will be populated next
        }
        context.user_data['state'] = 'waiting_for_button_details'
        await update.message.reply_text(
            "🔗 Media and caption saved. \n"
            "Now, please send the text and URL for each button. You have two options:\n"
            "1. `Button Text | Button URL` (e.g., `Main Channel | https://t.me/your_channel`)\n"
            "2. Just paste a URL (e.g., `https://example.com/download`). The button text will be 'Download Now'.\n"
            "Use a new line for each button. Type `DONE` when finished.\n"
            "If there are no buttons, just type `DONE`."
        )
    else:
        # This media is not part of the addpost process, ignore or handle generally
        pass

@restricted
async def receive_button_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Receives button details and saves the post."""
    if context.user_data.get('state') == 'waiting_for_button_details':
        text = update.message.text.strip()
        temp_post = context.user_data.get('temp_post')
        post_name = context.user_data.get('new_post_name')

        if text.lower() == 'done':
            # Save the post
            posts_data[post_name] = temp_post
            save_data(posts_data, POSTS_FILE)

            await update.message.reply_text(
                f"🎉 Post '{post_name}' successfully saved!\n"
                f"It can now be searched using `/search {post_name}`."
            )
            # Clean up user_data state
            context.user_data.pop('state', None)
            context.user_data.pop('new_post_name', None)
            context.user_data.pop('temp_post', None)
        else:
            # Parse button text and URL
            parts = text.split('|', 1)
            if len(parts) == 2:
                button_text = parts[0].strip()
                button_url = parts[1].strip()
                # Basic URL validation
                if not re.match(r'https?://[^\s/$.?#].[^\s]*', button_url):
                    await update.message.reply_text("❌ Invalid URL. Please provide a valid URL.")
                    return
                temp_post['buttons'].append({"text": button_text, "url": button_url})
                await update.message.reply_text(f"✅ Button added: '{button_text}' -> '{button_url}'\n"
                                                "Add more buttons or type `DONE`.")
            elif len(parts) == 1 and re.match(r'https?://[^\s/$.?#].[^\s]*', text): # Check if it's just a URL
                button_url = text.strip()
                button_text = "Download Now" # Default text for URL-only input
                temp_post['buttons'].append({"text": button_text, "url": button_url})
                await update.message.reply_text(f"✅ Button added: '{button_text}' -> '{button_url}'\n"
                                                "Add more buttons or type `DONE`.")
            else:
                await update.message.reply_text("❌ Invalid format. Please use `Button Text | Button URL` or just a valid URL.")
    else:
        # Not in button details state, ignore or handle generally
        pass

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Searches for an anime post by name."""
    query = " ".join(context.args).strip()
    if not query:
        await update.message.reply_text(
            "🔎 Please enter the anime name in `/search <anime name>` format.\n"
            "Example: `/search The Shiunji Family Children`"
        )
        return

    found_post = None
    post_name_lower = query.lower()
    for name, post in posts_data.items():
        if post_name_lower in name.lower():
            found_post = post
            break

    if found_post:
        keyboard_buttons = []
        for btn in found_post.get('buttons', []):
            keyboard_buttons.append([InlineKeyboardButton(btn['text'], url=btn['url'])])
        reply_markup = InlineKeyboardMarkup(keyboard_buttons) if keyboard_buttons else None

        if found_post['media_type'] == 'photo':
            await update.message.reply_photo(
                photo=found_post['file_id'],
                caption=found_post['caption'],
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        elif found_post['media_type'] == 'video':
            await update.message.reply_video(
                video=found_post['file_id'],
                caption=found_post['caption'],
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    else:
        await update.message.reply_text("😔 Sorry, no anime post found with that name.")

async def animelist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays a paginated list of anime names."""
    anime_names = sorted(posts_data.keys(), key=lambda x: x.lower())
    if not anime_names:
        await update.message.reply_text("😔 No anime is in the list yet.")
        return

    page_size = 20
    total_pages = (len(anime_names) + page_size - 1) // page_size
    current_page = context.user_data.get('animelist_page', 0)

    if current_page >= total_pages: # Reset if page becomes invalid
        current_page = 0
        context.user_data['animelist_page'] = 0

    start_index = current_page * page_size
    end_index = min(start_index + page_size, len(anime_names))
    
    current_page_anime = anime_names[start_index:end_index]
    
    list_text = "📋 **Anime List** (Page " + str(current_page + 1) + "/" + str(total_pages) + ")\n\n"
    for i, name in enumerate(current_page_anime):
        list_text += f"{start_index + i + 1}. {name}\n"

    reply_markup = get_animelist_pagination_keyboard(current_page, total_pages)

    if update.callback_query:
        await update.callback_query.message.edit_text(
            text=list_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            text=list_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    context.user_data['animelist_page'] = current_page # Store current page

async def requestanime_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles anime requests."""
    anime_request = " ".join(context.args).strip()
    user = update.effective_user

    if not anime_request:
        await update.message.reply_text(
            "📝 Please enter the anime name in `/requestanime <anime name>` format.\n"
            "Example: `/requestanime Naruto`"
        )
        return

    user_id_str = str(user.id)
    if user_id_str not in requests_data:
        requests_data[user_id_str] = {
            "username": user.username if user.username else user.full_name,
            "chat_id": user.id,
            "requests": []
        }
    
    requests_data[user_id_str]["requests"].append(anime_request)
    save_data(requests_data, REQUESTS_FILE)

    # Forward request to admin group
    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=(f"🚨 **New Anime Request!**\n\n"
                  f"From: @{user.username if user.username else user.full_name} (ID: {user.id})\n"
                  f"Anime: *{anime_request}*"),
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "✅ Your anime request has been successfully submitted and forwarded to admins! ✨"
        )
    except Exception as e:
        logger.error(f"Error forwarding request to admin group: {e}")
        await update.message.reply_text(
            "✅ Your anime request has been successfully submitted, but there was an issue notifying admins. Please try again later."
        )


async def viewrequest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Views anime requests."""
    user = update.effective_user
    user_id_str = str(user.id)

    request_list_text = "📜 **Your Anime Request List**\n\n"
    has_requests = False

    if user.id in ADMIN_IDS:
        # Admin can view all requests
        request_list_text = "📋 **All Anime Requests**\n\n"
        if not requests_data:
            request_list_text += "😔 No requests yet."
        else:
            for uid, data in requests_data.items():
                username = data.get("username", f"User {uid}")
                requests = data.get("requests", [])
                if requests:
                    request_list_text += f"**@{username}**:\n"
                    for i, req in enumerate(requests):
                        request_list_text += f"  {i+1}. {req}\n"
                    request_list_text += "\n"
                    has_requests = True
            if not has_requests:
                request_list_text += "😔 No requests yet."
    else:
        # Regular user views only their own requests
        if user_id_str in requests_data and requests_data[user_id_str]["requests"]:
            requests = requests_data[user_id_str]["requests"]
            for i, req in enumerate(requests):
                request_list_text += f"  {i+1}. {req}\n"
            has_requests = True
        else:
            request_list_text += "😔 You have not made any anime requests yet."

    await update.message.reply_text(request_list_text, parse_mode="Markdown")

@restricted
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcasts a message to all users who have started the bot."""
    message_to_send = " ".join(context.args)
    if not message_to_send:
        await update.message.reply_text("📢 Please enter the message to broadcast.\nExample: `/broadcast New anime is available!`")
        return

    success_count = 0
    fail_count = 0
    total_users = len(users_data)

    await update.message.reply_text(f"⏳ Starting to broadcast message to {total_users} users...")

    for user_id_str in users_data:
        try:
            await context.bot.send_message(chat_id=int(user_id_str), text=message_to_send, parse_mode="Markdown")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to user {user_id_str}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"✅ Broadcast complete!\n"
        f"Successfully sent: {success_count} ✨\n"
        f"Failed to send: {fail_count} ❌"
    )

@restricted
async def notifyrequest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Notifies a user about their requested anime."""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "🔔 Please use the format `/notifyrequest <username> <message>`.\n"
            "The message can include anime availability or a search link."
        )
        return

    target_username = args[0].lstrip('@') # Remove leading '@' if present
    notification_message = " ".join(args[1:])
    
    target_chat_id = None
    found_user_data = None
    for user_id_str, user_req_data in requests_data.items():
        if user_req_data.get("username", "").lower() == target_username.lower():
            target_chat_id = user_req_data["chat_id"]
            found_user_data = user_req_data
            break

    if target_chat_id:
        try:
            await context.bot.send_message(
                chat_id=target_chat_id,
                text=f"🔔 Your Anime Request Update! ✨\n\n"
                     f"{notification_message}\n\n"
                     f"You can search for it using the `/search` command."
            )
            await update.message.reply_text(f"✅ Successfully notified user @{target_username}!")
            
            # Optionally, remove the fulfilled request from the list
            # You might want to modify this logic if multiple requests for same anime are possible
            # For now, let's just keep the request history
            # if found_user_data and found_user_data["requests"]:
            #     pass 

        except Exception as e:
            logger.error(f"Failed to notify user {target_username} (ID: {target_chat_id}): {e}")
            await update.message.reply_text(f"❌ Failed to notify user @{target_username}.")
    else:
        await update.message.reply_text(f"😔 User '@{target_username}' not found or has not made any requests.")


# --- Callback Query Handler ---
async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline keyboard button presses."""
    query = update.callback_query
    await query.answer() # Acknowledge the button press

    if query.data == "about_btn":
        caption = (
            "🌟 **About Us**\n\n"
            "Our goal is to help you find your favorite anime all in one place. "
            "We strive to provide the latest releases and popular series.\n\n"
            "Stay connected with us and follow our channel:\n"
            f"[Main Channel]({CHANNEL_LINK})\n\n"
            "For any questions or suggestions, please contact us on our channel."
        )
        await query.message.edit_media(
            media=telegram.InputMediaPhoto(media=ABOUT_IMAGE_URL, caption=caption),
            reply_markup=get_about_help_keyboard(),
        )
    elif query.data == "help_btn":
        await help_command(update, context) # Re-use help command logic
    elif query.data == "close_btn":
        await query.message.delete()
    elif query.data == "back_to_start_btn":
        caption = (
            f"👋 Hello {query.from_user.first_name}! Welcome to your Anime Channel Bot.✨\n\n"
            "You can find your favorite anime here, check new releases and much more.\n\n"
            "Use the buttons below or these commands:\n\n"
            "✨ `/search <anime name>` - Search for an anime\n"
            "📋 `/Animelist` - See the list of available anime\n"
            "📝 `/requestanime <anime name>` - Request a new anime\n"
            "❓ `/help` - Get all commands and information"
        )
        await query.message.edit_media(
            media=telegram.InputMediaPhoto(media=START_IMAGE_URL, caption=caption),
            reply_markup=get_start_keyboard(),
        )
    elif query.data.startswith("animelist_"):
        parts = query.data.split('_')
        action = parts[1]
        current_page = int(parts[2])
        
        if action == "next":
            context.user_data['animelist_page'] = current_page + 1
        elif action == "prev":
            context.user_data['animelist_page'] = current_page - 1
        
        await animelist_command(update, context) # Re-call animelist to update

async def generic_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles general text messages if not part of a specific state."""
    # If the bot is waiting for a post name or button details, these handlers will take precedence.
    # Otherwise, this handler will respond.
    if not context.user_data.get('state'):
        await update.message.reply_text(
            "🤔 I didn't understand that. Please use the `/help` command to see available commands."
        )


def main() -> None:
    """Starts the bot."""
    # Load data on startup
    init_data_stores()

    # Create the Application and pass your bot's token.
    application = Application.builder().token(BOT_TOKEN).build()

    # --- Register Handlers ---
    # Command Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addpost", addpost_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("Animelist", animelist_command)) # Case sensitive for consistency
    application.add_handler(CommandHandler("requestanime", requestanime_command))
    application.add_handler(CommandHandler("viewrequest", viewrequest_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("notifyrequest", notifyrequest_command))

    # Message Handlers
    # For receiving post name after /addpost
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, receive_post_name)
    )
    # For receiving media with caption (for addpost)
    application.add_handler(
        MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE | filters.VIDEO & filters.ChatType.PRIVATE, handle_post_media)
    )
    # For receiving button details after media
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, receive_button_details)
    )
    # Generic message handler for anything else
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, generic_message_handler)
    )

    # Callback Query Handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback_handler))

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    logger.info("Bot stopped.")

if __name__ == '__main__':
    main()

