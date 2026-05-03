"""
Telegram AI Bot - 100% FREE VERSION
- Chat powered by Google Gemini (free tier)
- Image generation powered by Pollinations.ai (completely free, no API key)
- Per-user conversation history
- Admin controls
"""

import os
import logging
import urllib.parse
import requests
from dotenv import load_dotenv
from datetime import datetime
import google.genai as genai
from telegram import Update, constants
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import tempfile
from PIL import Image
from io import BytesIO
import numpy as np
import imageio

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")

# Optional: comma-separated Telegram user IDs allowed to use the bot.
# Leave empty in .env to allow everyone.
ALLOWED_USERS_RAW  = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS   = set(
    int(uid.strip()) for uid in ALLOWED_USERS_RAW.split(",") if uid.strip()
)

# Admin user ID (only this user can use /clear_all)
ADMIN_USER_ID_STR  = os.getenv("ADMIN_USER_ID", "").strip()
ADMIN_USER_ID      = int(ADMIN_USER_ID_STR) if ADMIN_USER_ID_STR else 0

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Gemini AI setup ───────────────────────────────────────────────────────────
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# ── Per-user Gemini chat sessions  {user_id: ChatSession} ────────────────────
# Store conversation history for each user
chat_sessions: dict[int, list] = {}

MAX_HISTORY = 50  # Keep conversation history

# ── Bot statistics ────────────────────────────────────────────────────────────
bot_stats = {
    "total_chats": 0,
    "total_images": 0,
    "total_videos": 0,
    "total_jokes": 0,
    "total_quotes": 0,
    "total_translations": 0,
    "total_summarizations": 0,
    "start_time": datetime.now(),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_allowed(user_id: int) -> bool:
    if not ALLOWED_USER_IDS:
        return True
    return user_id in ALLOWED_USER_IDS


def get_chat_session(user_id: int) -> list:
    """Get or create conversation history for user."""
    if user_id not in chat_sessions:
        chat_sessions[user_id] = [
            {
                "role": "user",
                "parts": "You are a helpful, friendly, and knowledgeable AI assistant inside a Telegram bot. Keep responses concise and well-formatted for Telegram (use plain text). Be conversational, warm, and direct."
            }
        ]
    return chat_sessions[user_id]


def clear_session(user_id: int) -> None:
    """Clear conversation history for user."""
    if user_id in chat_sessions:
        del chat_sessions[user_id]


def generate_image_url(prompt: str) -> str:
    """Generate image URL using Pollinations.ai (100% free, no API key needed)."""
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&nologo=true&enhance=true"


def create_animated_video(prompt: str, num_frames: int = 4, fps: int = 2) -> str:
    """Create an animated video by generating multiple image variations."""
    frames = []
    
    try:
        # Generate variations of the prompt for each frame
        variations = [
            f"{prompt}",
            f"{prompt}, alternative style",
            f"{prompt}, different perspective",
            f"{prompt}, another variation",
        ][:num_frames]
        
        for i, variation in enumerate(variations):
            try:
                image_url = generate_image_url(variation)
                response = requests.get(image_url, timeout=30)
                response.raise_for_status()
                
                # Convert to PIL Image
                img = Image.open(BytesIO(response.content))
                # Resize for consistency
                img = img.resize((512, 512))
                frames.append(img)
                logger.info(f"Generated frame {i+1}/{num_frames}")
            except Exception as e:
                logger.error(f"Error downloading frame {i+1}: {e}")
                if not frames:
                    raise
        
        if not frames:
            raise Exception("Could not generate any frames")
        
        # Create temporary video file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            video_path = tmp_file.name
        
        # Convert PIL images to numpy arrays and save as video
        frame_arrays = [np.array(frame) for frame in frames]
        imageio.mimsave(video_path, frame_arrays, fps=fps, codec='libx264')
        
        return video_path
    except Exception as e:
        logger.error(f"Video creation error: {e}")
        raise


# ── Command handlers ──────────────────────────────────────────────────────────

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    admin_section = "\n🗑️ /clear_all — clear all user histories" if user.id == ADMIN_USER_ID else ""

    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        "I'm your FREE AI assistant powered by Google Gemini & Pollinations.ai\n\n"
        "Here's what I can do:\n"
        "💬 Just send me any message — I'll reply like ChatGPT!\n"
        "🎨 /image <prompt> — generate a free AI image\n"
        "🎬 /video <prompt> — generate an AI animated video\n"
        "😂 /joke — get a funny joke\n"
        "✨ /quote — get an inspiring quote\n"
        "🌐 /translate <text> to <language> — translate text\n"
        "📝 /summarize — summarize long text (reply to message)\n"
        "✂️ /shorten — shorten a text (reply to message)\n"
        "📊 /stats — view bot usage statistics\n"
        "🔄 /reset — clear your conversation history"
        f"{admin_section}\n"
        "ℹ️ /help — show this message again\n\n"
        "Let's go! What's on your mind?",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start_command(update, context)


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    clear_session(user.id)
    await update.message.reply_text("🔄 Conversation cleared! Let's start fresh.")


async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text(
            "🎨 Please add a description after the command.\n"
            "Example: /image a sunset over the ocean, oil painting style"
        )
        return

    await update.message.chat.send_action(constants.ChatAction.UPLOAD_PHOTO)
    thinking_msg = await update.message.reply_text("🎨 Generating your image, please wait…")

    try:
        image_url = generate_image_url(prompt)

        # Download and send the image
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        await thinking_msg.delete()
        await update.message.reply_photo(
            photo=response.content,
            caption=f"🎨 Your image is ready!\n\n📝 {prompt}",
        )
        bot_stats["total_images"] += 1
    except Exception as e:
        logger.error("Image generation error: %s", e)
        await thinking_msg.edit_text(
            "❌ Image generation failed. Please try a different prompt or try again."
        )


async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    prompt = " ".join(context.args) if context.args else ""
    if not prompt:
        await update.message.reply_text(
            "🎬 Please add a description after the command.\n"
            "Example: /video a spaceship flying through the galaxy"
        )
        return

    await update.message.chat.send_action(constants.ChatAction.UPLOAD_VIDEO)
    thinking_msg = await update.message.reply_text("🎬 Generating your video (4 frames)… this may take a minute…")

    try:
        video_path = create_animated_video(prompt, num_frames=4, fps=2)
        
        with open(video_path, 'rb') as video_file:
            await thinking_msg.delete()
            await update.message.reply_video(
                video=video_file,
                caption=f"🎬 Your video is ready!\n\n📝 {prompt}",
                supports_streaming=True,
            )
        
        # Cleanup
        import os as os_module
        os_module.remove(video_path)
        bot_stats["total_videos"] += 1
        
    except Exception as e:
        logger.error("Video generation error: %s", e)
        await thinking_msg.edit_text(
            "❌ Video generation failed. Please try a simpler prompt or try again.\n\n"
            "Note: This feature generates 4 AI images and combines them into an animated video."
        )


async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    await update.message.chat.send_action(constants.ChatAction.TYPING)
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Tell me one funny and original joke. Make it short and witty."
        )
        joke = response.text
        await update.message.reply_text(f"😂 {joke}")
        bot_stats["total_jokes"] += 1
    except Exception as e:
        logger.error("Joke generation error: %s", e)
        await update.message.reply_text("❌ Failed to generate joke. Try again!")


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    await update.message.chat.send_action(constants.ChatAction.TYPING)
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Share one inspiring or thoughtful quote with attribution. Keep it under 100 words."
        )
        quote = response.text
        await update.message.reply_text(f"✨ {quote}")
        bot_stats["total_quotes"] += 1
    except Exception as e:
        logger.error("Quote generation error: %s", e)
        await update.message.reply_text("❌ Failed to generate quote. Try again!")


async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            "🌐 Usage: /translate <text> to <language>\n"
            "Example: /translate Hello world to Spanish"
        )
        return

    # Parse command: text to language
    try:
        to_index = context.args.index("to")
        text = " ".join(context.args[:to_index])
        language = " ".join(context.args[to_index + 1:])
    except ValueError:
        await update.message.reply_text("❌ Format: /translate <text> to <language>")
        return

    await update.message.chat.send_action(constants.ChatAction.TYPING)
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Translate this text to {language}:\n\n{text}\n\nProvide only the translation, no explanation."
        )
        translation = response.text
        await update.message.reply_text(f"🌐 **{language}:**\n{translation}")
        bot_stats["total_translations"] += 1
    except Exception as e:
        logger.error("Translation error: %s", e)
        await update.message.reply_text("❌ Translation failed. Try again!")


async def summarize_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    # Get text from command args or from replied message
    text_to_summarize = None
    if context.args:
        text_to_summarize = " ".join(context.args)
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        text_to_summarize = update.message.reply_to_message.text
    
    if not text_to_summarize:
        await update.message.reply_text(
            "📝 Usage: /summarize <text>\n"
            "Or reply to a message with /summarize"
        )
        return

    await update.message.chat.send_action(constants.ChatAction.TYPING)
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Summarize this text in 2-3 sentences:\n\n{text_to_summarize}"
        )
        summary = response.text
        await update.message.reply_text(f"📝 **Summary:**\n{summary}")
        bot_stats["total_summarizations"] += 1
    except Exception as e:
        logger.error("Summarization error: %s", e)
        await update.message.reply_text("❌ Summarization failed. Try again!")


async def shorten_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    # Get text from command args or from replied message
    text_to_shorten = None
    if context.args:
        text_to_shorten = " ".join(context.args)
    elif update.message.reply_to_message and update.message.reply_to_message.text:
        text_to_shorten = update.message.reply_to_message.text
    
    if not text_to_shorten:
        await update.message.reply_text(
            "✂️ Usage: /shorten <text>\n"
            "Or reply to a message with /shorten"
        )
        return

    await update.message.chat.send_action(constants.ChatAction.TYPING)
    try:
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Shorten this text to 1-2 sentences while keeping the main idea:\n\n{text_to_shorten}"
        )
        shortened = response.text
        await update.message.reply_text(f"✂️ **Shortened:**\n{shortened}")
    except Exception as e:
        logger.error("Shorten error: %s", e)
        await update.message.reply_text("❌ Failed to shorten. Try again!")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    uptime = datetime.now() - bot_stats["start_time"]
    uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

    stats_text = (
        f"📊 **Bot Statistics**\n\n"
        f"⏱️ Uptime: {uptime_str}\n"
        f"💬 Chat messages: {bot_stats['total_chats']}\n"
        f"🎨 Images generated: {bot_stats['total_images']}\n"
        f"🎬 Videos generated: {bot_stats['total_videos']}\n"
        f"😂 Jokes told: {bot_stats['total_jokes']}\n"
        f"✨ Quotes shared: {bot_stats['total_quotes']}\n"
        f"🌐 Translations: {bot_stats['total_translations']}\n"
        f"📝 Summarizations: {bot_stats['total_summarizations']}"
    )
    await update.message.reply_text(stats_text)


async def clear_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    
    # Only allow the admin user
    if user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ This command is admin-only. Only your user can access it.")
        return

    chat_sessions.clear()
    await update.message.reply_text("🗑️ All conversation histories cleared!")
    logger.info("Admin %s cleared all chat sessions", user.id)


async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_allowed(user.id):
        await update.message.reply_text("⛔ Sorry, you are not authorised to use this bot.")
        return

    user_text = update.message.text.strip()
    if not user_text:
        return

    await update.message.chat.send_action(constants.ChatAction.TYPING)

    try:
        # Get or create user's conversation history
        history = get_chat_session(user.id)
        
        # Add user message to history
        history.append({
            "role": "user",
            "parts": user_text
        })
        
        # Keep only last MAX_HISTORY messages (excluding system message)
        if len(history) > MAX_HISTORY:
            history = [history[0]] + history[-(MAX_HISTORY-1):]
            chat_sessions[user.id] = history
        
        # Generate response with streaming for faster feedback
        full_response = ""
        for chunk in genai_client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=history
        ):
            if chunk.text:
                full_response += chunk.text
        
        reply = full_response
        
        # Add assistant response to history
        history.append({
            "role": "assistant",
            "parts": reply
        })

        # Telegram has a 4096-char limit
        if len(reply) > 4000:
            chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(reply)

        bot_stats["total_chats"] += 1

    except Exception as e:
        logger.error("Gemini API error: %s", e)
        await update.message.reply_text(
            "❌ Something went wrong. Please try again."
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Update %s caused error: %s", update, context.error)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in your .env file.")
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in your .env file.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  start_command))
    app.add_handler(CommandHandler("help",   help_command))
    app.add_handler(CommandHandler("reset",  reset_command))
    app.add_handler(CommandHandler("image",  image_command))
    app.add_handler(CommandHandler("video",  video_command))
    app.add_handler(CommandHandler("joke",   joke_command))
    app.add_handler(CommandHandler("quote",  quote_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("summarize", summarize_command))
    app.add_handler(CommandHandler("shorten", shorten_command))
    app.add_handler(CommandHandler("stats",  stats_command))
    app.add_handler(CommandHandler("clear_all", clear_all_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message))
    app.add_error_handler(error_handler)

    logger.info("Bot is starting… (FREE version with Gemini + Pollinations.ai)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
