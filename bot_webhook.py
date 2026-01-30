#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Webhook version of Moe Prostranstvo bot for web service deployment
"""

import os
import logging
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

# Initialize Flask app
app = Flask(__name__)

# Get configuration from environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Your web service URL
PORT = int(os.getenv("PORT", 8080))

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# Initialize bot application
application = Application.builder().token(TOKEN).build()

# Add all handlers from bot.py
def setup_handlers():
    """Setup all bot handlers"""
    application.add_handler(CommandHandler("start", bot.start))
    
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
    application.add_handler(tarot_conv)
    
    # Diary conversation handler
    diary_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.diary_new_entry, pattern="^diary_new$")],
        states={
            bot.DIARY_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.diary_save_entry)]
        },
        fallbacks=[CommandHandler("cancel", bot.cancel)]
    )
    application.add_handler(diary_conv)
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(bot.callback_router))
    
    # Text message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_message))

setup_handlers()


@app.route('/')
def index():
    """Health check endpoint"""
    return "Moe Prostranstvo Bot is running! 🌿", 200


@app.route('/health')
def health():
    """Health check for monitoring"""
    return {"status": "healthy", "bot": "moe_prostranstvo"}, 200


@app.route(f'/{TOKEN}', methods=['POST'])
async def webhook():
    """Handle incoming webhook updates from Telegram"""
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return "Error", 500


def setup_webhook():
    """Setup webhook with Telegram"""
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")
        import asyncio
        asyncio.run(application.bot.set_webhook(url=webhook_url))
        logger.info("Webhook set successfully!")
    else:
        logger.warning("WEBHOOK_URL not set. Webhook not configured.")


if __name__ == '__main__':
    # Setup webhook on startup
    setup_webhook()
    
    # Run Flask app
    logger.info(f"Starting webhook server on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
