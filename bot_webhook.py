#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Webhook version of Moe Prostranstvo bot for web service deployment
"""
import os
import logging
import asyncio
from flask import Flask, request, jsonify
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
PORT = int(os.getenv("PORT", 10000))

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL environment variable not set")

# Initialize Flask app
app = Flask(__name__)

# Initialize bot application globally
application = None
webhook_configured = False
event_loop = None


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
        fallbacks=[CommandHandler("cancel", bot.cancel)],
        per_message=False,
        per_chat=True,
        per_user=True
    )
    app_instance.add_handler(tarot_conv)
    
    # Diary conversation handler
    diary_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(bot.diary_new_entry, pattern="^diary_new$")],
        states={
            bot.DIARY_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, bot.diary_save_entry)]
        },
        fallbacks=[CommandHandler("cancel", bot.cancel)],
        per_message=False,
        per_chat=True,
        per_user=True
    )
    app_instance.add_handler(diary_conv)
    
    # Callback query handler (must be after ConversationHandlers)
    app_instance.add_handler(CallbackQueryHandler(bot.callback_router))
    
    # Text message handler
    app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text_message))


def init_bot():
    """Initialize bot application and setup webhook"""
    global application, webhook_configured, event_loop
    
    logger.info("Initializing bot application...")
    
    # Create persistent event loop
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)
    
    try:
        # Initialize application
        application = Application.builder().token(TOKEN).build()
        
        # Setup handlers
        setup_handlers(application)
        
        # Initialize the application
        event_loop.run_until_complete(application.initialize())
        event_loop.run_until_complete(application.bot.initialize())
        
        # Setup webhook
        webhook_url = f"{WEBHOOK_URL}/{TOKEN}"
        logger.info(f"Setting webhook to: {webhook_url}")
        event_loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
        logger.info("✅ Webhook set successfully!")
        
        # Start the application
        event_loop.run_until_complete(application.start())
        logger.info("✅ Application started successfully!")
        
        webhook_configured = True
        
    except Exception as e:
        logger.error(f"❌ Error initializing bot: {e}")
        raise


# Initialize bot on startup
logger.info("=" * 60)
logger.info("Starting Moe Prostranstvo Bot (Webhook Mode)")
logger.info("=" * 60)
init_bot()


@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot": "moe_prostranstvo",
        "webhook_configured": webhook_configured
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "bot": "moe_prostranstvo",
        "webhook_configured": webhook_configured
    })


@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    """Handle incoming updates from Telegram"""
    if not application or not event_loop:
        logger.error("Application not initialized")
        return jsonify({"error": "Bot not initialized"}), 500
    
    try:
        # Get update from request
        update_data = request.get_json(force=True)
        
        # Create Update object
        update = Update.de_json(update_data, application.bot)
        
        # Process update using the persistent event loop
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(application.process_update(update))
        
        return jsonify({"ok": True})
    
    except Exception as e:
        logger.error(f"Error processing update: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info(f"Your service is live 🎉")
    logger.info("")
    logger.info("/" * 60)
    logger.info("")
    logger.info(f"Available at your primary URL {WEBHOOK_URL}")
    logger.info("")
    logger.info("/" * 60)
    logger.info("")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=PORT, debug=False)
