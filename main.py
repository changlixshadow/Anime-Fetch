import os
import json
from flask import Flask, request, abort
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputFile
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# --- Configuration ---
# IMPORTANT: For Render, set these as actual Environment Variables in your service settings.
# The default values here are just for local testing if env vars aren't set.
API_TOKEN = os.getenv("TELEGRAM_API_TOKEN", "8006836827:AAERFD1tDpBDJhvKm_AHy20uSAzZdoRwbZc")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://anime-fetch-j2ro.onrender.com/webhook")
ADMIN_IDS = json.loads(os.getenv("ADMIN_IDS", "[5759232282]"))

POSTS_FILE = "posts.json"
REQUESTS_FILE = "requests.json"

# State for ConversationHandler
ADD_POST_NAME, ADD_POST_BUTTON, ADD_POST_CONFIRM = range(3)

START_IMAGE = "https://telegra.ph/file/050a20dace942a60220c0-6afbc023e43fad29c7.jpg"
ABOUT_IMAGE = "https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg"
HELP_IMAGE = "https://telegra.ph/file/e6ec31fc792d072da2b7e-54e2f9d4c5651823b3.jpg" # Corrected this link to a valid image
DEFAULT_POST_IMAGE = "https://telegra.ph/file/9d18345731db88fff4f8c-d2b3920631195c5747.jpg" # Fallback if no media is sent

app = Flask(__name__)
application = None # Initialize Application instance later

# --- Helper Functions ---
def ensure_file(file):
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)

def load_json(file):
    ensure_file(file)
    with open(file, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {} # Return empty dict if JSON is invalid/empty

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

# --- Keyboard Markups ---
def start_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("About 📜", callback_data="about"),
         InlineKeyboardButton("Help ⚙️", callback_data="help")],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ])

# --- Callbacks for Start/Help/About/Close ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "✨ <b>Welcome to Anime Garden!</b> ✨\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel\n"
    )
    await update.message.reply_photo(photo=START_IMAGE, caption=caption,
                                     parse_mode=ParseMode.HTML, reply_markup=start_buttons())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>⚙ Help Guide</b>\n\n"
        "▶ /search &lt;name&gt; - Find anime\n"
        "▶ /animelist - Show list of anime\n"
        "▶ /requestanime &lt;name&gt; - Request new anime\n\n"
        "<b>Admins Only:</b>\n"
        "✔ /addpost - Add a new anime post\n"
        "✔ /viewrequests - View pending anime requests"
    )
    if update.message:
        await update.message.reply_photo(photo=HELP_IMAGE, caption=caption, parse_mode=ParseMode.HTML, reply_markup=back_button())
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_media(
            media=InputMediaPhoto(media=HELP_IMAGE, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=back_button()
        )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = (
        "<b>📜 About Anime Garden Bot</b>\n\n"
        "This bot helps you find and request anime.\n"
        "It's designed to be user-friendly and efficient.\n\n"
        "<b>Version:</b> 1.0\n"
        "<b>Developer:</b> Your Name/Team\n"
        "<b>Source:</b> [Link to GitHub if open source]"
    )
    if update.message:
        await update.message.reply_photo(photo=ABOUT_IMAGE, caption=caption, parse_mode=ParseMode.HTML, reply_markup=back_button())
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_media(
            media=InputMediaPhoto(media=ABOUT_IMAGE, caption=caption, parse_mode=ParseMode.HTML),
            reply_markup=back_button()
        )

async def close_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(caption="Bot interaction closed.", reply_markup=None) # Remove buttons

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    caption = (
        "✨ <b>Welcome to Anime Garden!</b> ✨\n\n"
        "Discover & Request your favorite Anime.\n"
        "Use the buttons below to explore more!\n\n"
        "<b>Channel:</b> @YourMainChannel\n"
        "<b>Backup:</b> @YourBackupChannel\n"
    )
    await query.edit_message_media(
        media=InputMediaPhoto(media=START_IMAGE, caption=caption, parse_mode=ParseMode.HTML),
        reply_markup=start_buttons()
    )

# --- Admin Functionality: Add Post (ConversationHandler) ---
async def start_addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 You are not authorized to use this command.")
        return ConversationHandler.END

    if not update.message.photo and not update.message.video and not update.message.reply_to_message:
        await update.message.reply_text(
            "Please send the media (photo or video) for the post first, "
            "then use /addpost as a reply to that media.\n"
            "If you want to add a post without media, simply use /addpost and I'll use a default image."
        )
        context.user_data['media_type'] = 'photo'
        context.user_data['file_id'] = DEFAULT_POST_IMAGE
        context.user_data['caption'] = "" # Initialize caption
        await update.message.reply_text("Now, what's the name of the anime for this post?")
        return ADD_POST_NAME
    
    # If /addpost is a reply to media
    if update.message.reply_to_message:
        replied_message = update.message.reply_to_message
        if replied_message.photo:
            context.user_data['media_type'] = 'photo'
            context.user_data['file_id'] = replied_message.photo[-1].file_id
        elif replied_message.video:
            context.user_data['media_type'] = 'video'
            context.user_data['file_id'] = replied_message.video.file_id
        else:
            await update.message.reply_text(
                "The replied message does not contain a photo or video. "
                "Please reply to a photo or video, or use /addpost without reply for default image."
            )
            return ConversationHandler.END

        context.user_data['caption'] = replied_message.caption or ""
        await update.message.reply_text("Okay, I've got the media and existing caption. Now, what's the **name** of the anime for this post?")
        return ADD_POST_NAME
    else: # If /addpost is sent directly without reply but we still want to add media
        await update.message.reply_text("Please send the media (photo or video) for the post now. Once sent, then use /addpost command again.")
        return ConversationHandler.END


async def get_post_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post_name = update.message.text
    if not post_name:
        await update.message.reply_text("Anime name cannot be empty. Please enter the name.")
        return ADD_POST_NAME # Stay in the same state

    context.user_data['post_name'] = post_name
    await update.message.reply_text(
        "Great! Now, please provide the button text and link in the format:\n"
        "<code>Button Text | https://example.com/link</code>\n"
        "Or type 'none' if you don't want a button."
    , parse_mode=ParseMode.HTML)
    return ADD_POST_BUTTON

async def get_post_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button_input = update.message.text
    button_data = {}

    if button_input.lower() != 'none':
        parts = button_input.split('|', 1)
        if len(parts) == 2:
            button_text = parts[0].strip()
            button_url = parts[1].strip()
            if button_url.startswith(('http://', 'https://')):
                button_data = {"text": button_text, "url": button_url}
            else:
                await update.message.reply_text("Invalid URL. Please provide a valid URL starting with http:// or https://. Try again or type 'none'.")
                return ADD_POST_BUTTON
        else:
            await update.message.reply_text("Invalid format. Please use 'Button Text | https://example.com/link' or 'none'. Try again.")
            return ADD_POST_BUTTON

    context.user_data['button_data'] = button_data

    # Construct the final caption
    final_caption = f"<b>{context.user_data['post_name']}</b>\n\n"
    if context.user_data['caption']:
        final_caption += f"{context.user_data['caption']}\n\n"
    final_caption += "✨ Download Now ✨"

    context.user_data['final_caption'] = final_caption

    # Create a preview
    preview_markup = None
    if button_data:
        preview_markup = InlineKeyboardMarkup([[InlineKeyboardButton(button_data["text"], url=button_data["url"])]])

    await update.message.reply_text("Preview of your post:")
    try:
        if context.user_data['media_type'] == "photo":
            await update.message.reply_photo(
                photo=context.user_data['file_id'],
                caption=final_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=preview_markup
            )
        else: # Assuming video
            await update.message.reply_video(
                video=context.user_data['file_id'],
                caption=final_caption,
                parse_mode=ParseMode.HTML,
                reply_markup=preview_markup
            )
    except Exception as e:
        await update.message.reply_text(f"Error sending preview. Make sure the media file ID is valid. ({e})\nProceeding anyway, but post might fail if media is invalid.")
        # Optionally, you can cancel the conversation here if media errors are critical
        # return ConversationHandler.END

    await update.message.reply_text("Does this look correct? Type 'yes' to save, or 'no' to cancel.")
    return ADD_POST_CONFIRM

async def confirm_addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confirmation = update.message.text.lower()
    if confirmation == 'yes':
        posts = load_json(POSTS_FILE)
        post_id = str(len(posts) + 1)
        
        post_data = {
            "media_type": context.user_data.get('media_type', 'photo'), # Default to photo if not set
            "file_id": context.user_data.get('file_id', DEFAULT_POST_IMAGE), # Default to image if not set
            "caption": context.user_data.get('final_caption', ''),
            "button": context.user_data.get('button_data', {})
        }
        posts[post_id] = post_data
        save_json(POSTS_FILE, posts)
        await update.message.reply_text("✅ Post saved successfully!")
    else:
        await update.message.reply_text("🚫 Post addition cancelled.")

    context.user_data.clear() # Clear user data for the next conversation
    return ConversationHandler.END

async def cancel_addpost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚫 Post addition cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

# --- General User Functionality ---
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Click /help to see how the bot works.")

async def delete_unwanted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This handler can be problematic if it deletes messages from users who send non-command text
    # It's generally better to let non-command text pass or reply with a friendly message.
    # I've commented out the original deletion logic to avoid unintended behavior.
    pass

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    query = ' '.join(context.args).lower()
    if not query:
        await update.message.reply_text("❗ Usage: /search <anime name>")
        return

    found = False
    for post_id, post in posts.items():
        # Search in the caption (which includes the bolded name from addpost)
        if query in post.get("caption", "").lower():
            markup = None
            if post.get('button') and post['button'].get('text') and post['button'].get('url'):
                markup = InlineKeyboardMarkup([[InlineKeyboardButton(post['button']['text'], url=post['button']['url'])]])

            try:
                if post["media_type"] == "photo":
                    await update.message.reply_photo(
                        photo=post["file_id"],
                        caption=post["caption"],
                        parse_mode=ParseMode.HTML,
                        reply_markup=markup
                    )
                else: # Assuming video
                    await update.message.reply_video(
                        video=post["file_id"],
                        caption=post["caption"],
                        parse_mode=ParseMode.HTML,
                        reply_markup=markup
                    )
                found = True
            except Exception as e:
                print(f"Error sending post {post_id}: {e}")
                # You might want to handle invalid file_ids here, e.g., reply with text only
                await update.message.reply_text(f"Error displaying post (ID: {post_id}). Details:\n{post['caption']}", reply_markup=markup)
                found = True # Still considered found, just displayed differently

    if not found:
        await update.message.reply_text("❌ No matching anime found.")

async def requestanime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        return await update.message.reply_text("❗ Usage: /requestanime <anime name>")
    
    requests = load_json(REQUESTS_FILE)
    user_id = str(update.effective_user.id)
    
    # Initialize list if user has no requests
    if user_id not in requests:
        requests[user_id] = []
        
    requests[user_id].append(name)
    save_json(REQUESTS_FILE, requests)
    
    await update.message.reply_text("✅ Your request has been sent to the admins!")
    for admin in ADMIN_IDS:
        try:
            await context.bot.send_message(admin, f"📥 New request from {update.effective_user.first_name} (ID: {user_id}): {name}")
        except Exception as e:
            print(f"Failed to send message to admin {admin}: {e}")

async def notify_user(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    await context.bot.send_message(job.chat_id, text=f"✅ Your anime request '{job.data}' has been uploaded!")

async def viewrequests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    requests = load_json(REQUESTS_FILE)
    if update.effective_user.id in ADMIN_IDS:
        if not requests:
            msg = "No pending requests."
        else:
            msg = "<b>Pending Requests:</b>\n"
            for uid, reqs in requests.items():
                try:
                    user_info = await context.bot.get_chat(uid)
                    user_name = user_info.first_name if user_info.first_name else "N/A"
                    user_username = user_info.username if user_info.username else "N/A"
                    msg += f"\n• From {user_name} (@{user_username}, ID: {uid}):\n  - " + "\n  - ".join(reqs) + "\n"
                except Exception:
                    msg += f"\n• From Unknown User (ID: {uid}):\n  - " + "\n  - ".join(reqs) + "\n"
    else:
        user_id = str(update.effective_user.id)
        if user_id in requests and requests[user_id]:
            msg = "<b>Your Requests:</b>\n- " + "\n- ".join(requests[user_id])
        else:
            msg = "You have no pending requests."
            
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def animelist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    posts = load_json(POSTS_FILE)
    if not posts:
        target_message = update.message or update.callback_query.message
        await target_message.reply_text("No anime posts available yet.")
        return

    keys = list(posts.keys())
    
    # Determine current page
    page = 1
    if context.args and context.args[0].isdigit():
        page = int(context.args[0])
    elif update.callback_query and update.callback_query.data.startswith("page:"):
        page = int(update.callback_query.data.split(":")[1])

    per_page = 5
    total_pages = (len(keys) + per_page - 1) // per_page
    
    if not (1 <= page <= total_pages):
        page = 1 # Default to first page if invalid

    start_index = (page - 1) * per_page
    end_index = min(start_index + per_page, len(keys))
    
    display_posts = []
    for i in range(start_index, end_index):
        post_key = keys[i]
        post = posts[post_key]
        # Extract the bolded name from the caption
        caption_lines = post.get("caption", "").split('\n')
        name_line = caption_lines[0].strip('<b>').strip('</b>') if caption_lines else "Untitled"
        display_posts.append(f"{i + 1}. {name_line}")

    caption_text = "<b>Anime List:</b>\n\n" + "\n".join(display_posts)
    caption_text += f"\n\n<i>Page {page} of {total_pages}</i>"

    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{page-1}"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"page:{page+1}"))
    
    markup = InlineKeyboardMarkup([nav_buttons]) if nav_buttons else None
    
    if update.callback_query:
        await update.callback_query.edit_message_caption(caption=caption_text, parse_mode=ParseMode.HTML, reply_markup=markup)
        await update.callback_query.answer()
    else:
        await update.message.reply_text(caption_text, parse_mode=ParseMode.HTML, reply_markup=markup)


async def page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    context.args = [str(page)]
    # We need to pass the update object with the callback query to animelist
    await animelist(update, context)


# --- Webhook Integration for Flask ---
@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == "POST":
        # Ensure application is initialized
        if application is None:
            print("Telegram Application not initialized. Aborting webhook.")
            abort(500)

        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "ok"
    else:
        abort(405) # Method Not Allowed

# --- Main Application Setup ---
def setup_bot():
    global application
    ensure_file(POSTS_FILE)
    ensure_file(REQUESTS_FILE)

    application = Application.builder().token(API_TOKEN).build()

    # Conversation Handler for adding posts
    # Entry point is a command /addpost that is a reply OR a standalone /addpost
    add_post_entry_points = [
        CommandHandler("addpost", start_addpost, filters=filters.REPLY & (filters.PHOTO | filters.VIDEO)),
        CommandHandler("addpost", start_addpost, filters=~filters.REPLY) # For default image scenario
    ]

    add_post_handler = ConversationHandler(
        entry_points=add_post_entry_points,
        states={
            ADD_POST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_post_name)],
            ADD_POST_BUTTON: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_post_button)],
            ADD_POST_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_addpost)],
        },
        fallbacks=[CommandHandler("cancel", cancel_addpost)]
    )
    application.add_handler(add_post_handler)

    # Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("requestanime", requestanime))
    application.add_handler(CommandHandler("viewrequests", viewrequests))
    application.add_handler(CommandHandler("animelist", animelist))

    # Callback Query Handlers
    application.add_handler(CallbackQueryHandler(about_command, pattern="^about$"))
    application.add_handler(CallbackQueryHandler(help_command, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(close_command, pattern="^close$"))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern="^back$"))
    application.add_handler(CallbackQueryHandler(page_callback, pattern=r"^page:"))

    # Message Handlers
    application.add_handler(MessageHandler(filters.COMMAND, unknown))
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, delete_unwanted))
    
    print("Bot setup complete. Ready for webhook requests.")

if __name__ == '__main__':
    setup_bot() # Setup the Telegram Application and its handlers

    # Set up the webhook once when the application starts
    # This is done by your Render deployment's startup process
    # If this bot was the only thing running, you'd call run_webhook.
    # With Flask/Gunicorn, the webhook route handles the actual updates.
    # It's important to set the webhook URL ONCE externally after deployment.
    # The `gunicorn app:app` command will start Flask, and Flask will handle incoming requests.

    port = int(os.environ.get("PORT", 8080)) # Render provides PORT env variable
    print(f"Flask app running on port {port}")
    app.run(host="0.0.0.0", port=port)
