#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Webhook version of Moe Prostranstvo bot for web service deployment
"""

import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# Import bot handlers from main bot file
import bot

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get configuration from environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Your web service URL
PORT = int(os.getenv("PORT", 8080))

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# Initialize Flask app
app = Flask(__name__)

# Initialize bot application globally
application = None


def setup_handlers(app_instance):
    """Setup all bot handlers"""
    app_instance.add_handler(CommandHandler("start", bot.start))
    
    # Tarot conversation handler
    tarot_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(bot.tarot_bot_start, pattern="^tarot_bot$"),
            CallbackQueryHandler(bot.own_deck_layout_selected, pattern="^own_(1|2|3)cards$")
        ],
        states={
            bot.TAROT_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.tarot_question_received)],
            bot.TAROT_CARDS: [CallbackQueryHandler(bot.tarot_draw_cards, pattern="^tarot_(1|3)card")],
            bot.OWN_DECK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.own_deck_question_received)],
            bot.OWN_DECK_CARDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.own_deck_cards_received)]
        },
        fallbacks=[CommandHandler("cancel", bot.cancel)]
    )
    app_instance.add_handler(tarot_conv)
    
    # Diary conversation handler
    diary_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.diary_new_entry, pattern="^diary_new$")],
        states={
            bot.DIARY_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.diary_save_entry)]
        },
        fallbacks=[CommandHandler("cancel", bot.cancel)]
    )
    app_instance.add_handler(diary_conv)
    
    # Callback query handler
    app_instance.add_handler(CallbackQueryHandler(bot.callback_router))
    
    # Text message handler
    app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_message))


async def setup_webhook_async():
    """Setup webhook with Telegram asynchronously"""
    global application
    
    # Initialize application
    application = Application.builder().token(TOKEN).build()
    
    # Setup handlers
    setup_handlers(application)
    
    # Initialize the application
    await application.initialize()
    await application.bot.initialize()
    
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")
        await application.bot.set_webhook(url=webhook_url)
        logger.info("Webhook set successfully!")
    else:
        logger.warning("WEBHOOK_URL not set. Webhook not configured.")
    
    # Start the application
    await application.start()
    logger.info("Application started successfully!")


@app.route('/')
def index():
    """Health check endpoint"""
    return "Moe Prostranstvo Bot is running! 🌿", 200


@app.route('/health')
def health():
    """Health check for monitoring"""
    return {"status": "healthy", "bot": "moe_prostranstvo"}, 200


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Handle incoming webhook updates from Telegram"""
    try:
        if application is None:
            logger.error("Application not initialized")
            return "Application not ready", 503
        
        update = Update.de_json(request.get_json(force=True), application.bot)
        
        # Process update in async context
        asyncio.run(application.process_update(update))
        
        return "OK", 200
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return "Error", 500


def initialize_bot():
    """Initialize bot on startup"""
    logger.info("Initializing bot...")
    try:
        asyncio.run(setup_webhook_async())
        logger.info("Bot initialized successfully!")
    except Exception as e:
        logger.error(f"Failed to initialize bot: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    # Setup webhook on startup
    initialize_bot()
    
    # Run Flask app
    logger.info(f"Starting webhook server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
