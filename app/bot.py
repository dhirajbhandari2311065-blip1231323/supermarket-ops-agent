import logging
from typing import Any

from google import genai
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.agent.orchestrator import AgentOrchestrator
from app.agent.session import session_manager
from app.config import settings
from app.database.connection import AsyncSessionLocal, init_db

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Initialize Google GenAI client and Agent Orchestrator
gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
orchestrator = AgentOrchestrator(gemini_client=gemini_client)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command to welcome the user and reset active billing context."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    session_manager.reset_session(chat_id)

    welcome_text = (
        "🙏 **Namaste! Welcome to your Kirana AI Agent.**\n\n"
        "I can help you with:\n"
        "• 🛒 **Billing & Checkout** (e.g. 'Bill 2kg sugar and 1 Tata salt')\n"
        "• 📦 **Inventory & Stock Management** (e.g. 'Add stock 10 packets Maggi')\n"
        "• 📑 **Khata Credit Ledger** (e.g. 'Put 200 on Ramesh khata')\n"
        "• ⚙️ **Store Preferences** (e.g. 'Set default payment to UPI')\n\n"
        "Type `/new` at any time to clear the current bill context and start fresh."
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the active bill draft and resets context for the user."""
    if not update.effective_chat or not update.message:
        return

    chat_id = update.effective_chat.id
    session_manager.reset_session(chat_id)
    await update.message.reply_text("🔄 Session reset. Current billing context cleared.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Processes incoming chat messages through the AI Orchestrator within an async database session context."""
    if not update.effective_chat or not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()

    if not user_text:
        return

    # Indicate typing state to the user
    await update.message.chat.send_action(action="typing")

    async with AsyncSessionLocal() as db_session:
        try:
            response = await orchestrator.process_user_message(chat_id, db_session, user_text)

            # Attempt sending with Markdown formatting
            try:
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            except BadRequest as e:
                logger.warning(
                    f"Markdown parsing failed for response to chat {chat_id}: {e}. Retrying with plain text."
                )
                # Fallback to plain text if Markdown syntax from LLM output was invalid
                await update.message.reply_text(response)

        except Exception as e:
            logger.error(
                f"Unhandled error in message handler for chat {chat_id}: {e}", exc_info=True
            )
            await update.message.reply_text(
                "⚠️ **Service Notice**\n\n"
                "Both primary and backup LLM providers are currently busy or unavailable. "
                "Please wait a few seconds and try your request again."
            )


async def post_init(application: Any) -> None:
    """Initialize database connection pool on startup."""
    await init_db()
    logger.info("Database pool initialized successfully.")


def main():
    """Starts the Telegram bot polling listener."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set in .env")

    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting Telegram Bot listener...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()