#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import random
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Import utilities
from data.tarot_deck import get_full_deck, find_card
from utils.database import UserDatabase, DiaryDatabase, DailyEnergyCache
from utils.ai_generator import (
    generate_daily_energy,
    generate_tarot_reading,
    generate_own_deck_reading,
    generate_deeper_interpretation
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
TAROT_QUESTION, TAROT_CARDS, OWN_DECK_QUESTION, OWN_DECK_CARDS, DIARY_ENTRY = range(5)

# Main menu keyboard
def get_main_menu():
    """Get main menu keyboard"""
    keyboard = [
        ["⭐ Энергия дня", "🃏 Таро"],
        ["📝 Дневник", "🔔 Уведомления"],
        ["✨ Подписка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    UserDatabase.get_user(user_id)  # Initialize user
    
    welcome_text = """🌿 Добро пожаловать в «Моё пространство»

Это тихое место, где можно:
— задать вопрос Таро
— почувствовать энергию дня
— записать свои мысли и ощущения

Я не предсказываю будущее.
Я помогаю тебе услышать себя 🤍"""
    
    keyboard = [
        [InlineKeyboardButton("⭐ Энергия дня", callback_data="daily_energy")],
        [InlineKeyboardButton("🃏 Таро", callback_data="tarot")],
        [InlineKeyboardButton("📝 Дневник", callback_data="diary")],
        [InlineKeyboardButton("✨ Как это работает?", callback_data="how_it_works")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=get_main_menu()
    )


async def how_it_works(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explain how the bot works"""
    query = update.callback_query
    await query.answer()
    
    text = """✨ Как это работает?

🃏 **Таро** — задай вопрос, и карты помогут тебе услышать себя. Это не предсказание, а поддержка в размышлении.

⭐ **Энергия дня** — короткий астро-фон и карта дня с мягким советом.

📝 **Дневник** — твоё личное пространство для записей, мыслей и ощущений.

Это информационный и поддерживающий формат и не заменяет профессиональную консультацию."""
    
    await query.edit_message_text(text)


# ============================================
# DAILY ENERGY FEATURE
# ============================================

async def daily_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily energy request"""
    user_id = update.effective_user.id
    
    # Check if message or callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send_func = query.message.reply_text
    else:
        send_func = update.message.reply_text
    
    # Check usage limit
    if not UserDatabase.can_use_daily_energy(user_id):
        await send_func(
            "Ты уже получила энергию дня сегодня 🌿\n\n"
            "Приходи завтра за новой энергией, или оформи подписку для доступа к архиву.",
            reply_markup=get_main_menu()
        )
        return
    
    await send_func("Создаю энергию дня... ✨")
    
    # Check cache
    cached_energy = DailyEnergyCache.get_today()
    if cached_energy:
        energy_text = cached_energy["text"]
    else:
        energy_text = generate_daily_energy()
        DailyEnergyCache.set_today({"text": energy_text})
    
    # Record usage
    UserDatabase.record_daily_energy(user_id)
    
    # Store in context for diary
    context.user_data['last_daily_energy'] = energy_text
    
    # Buttons
    keyboard = [
        [InlineKeyboardButton("📝 Записать в дневник", callback_data="diary_save_daily")],
        [InlineKeyboardButton("🃏 Задать вопрос Таро", callback_data="tarot")],
        [InlineKeyboardButton("🔔 Напоминать ежедневно", callback_data="notify_daily")]
    ]
    
    if UserDatabase.is_paid(user_id):
        keyboard.append([InlineKeyboardButton("🌿 Углубить", callback_data="deepen_daily")])
    else:
        keyboard.append([InlineKeyboardButton("🌿 Углубить 🔒", callback_data="upgrade_needed")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_func(energy_text, reply_markup=reply_markup)


# ============================================
# TAROT FEATURE
# ============================================

async def tarot_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tarot mode selection"""
    user_id = update.effective_user.id
    
    # Check if message or callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send_func = query.message.reply_text
    else:
        send_func = update.message.reply_text
    
    text = "🃏 Как ты хочешь получить ответ?"
    
    keyboard = [
        [InlineKeyboardButton("✨ Карты выберет бот", callback_data="tarot_bot")],
    ]
    
    if UserDatabase.is_premium(user_id):
        keyboard.append([InlineKeyboardButton("🌿 У меня есть своя колода", callback_data="tarot_own")])
    else:
        keyboard.append([InlineKeyboardButton("🌿 У меня есть своя колода 🔒", callback_data="upgrade_premium")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_func(text, reply_markup=reply_markup)


async def tarot_bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start bot tarot reading"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Check usage limit
    if not UserDatabase.can_use_tarot(user_id):
        await query.message.reply_text(
            "Ты уже получила расклад Таро сегодня 🌿\n\n"
            "Приходи завтра за новым раскладом, или оформи подписку для безлимитного доступа.",
            reply_markup=get_main_menu()
        )
        return ConversationHandler.END
    
    await query.message.reply_text(
        "Задай свой вопрос. Сформулируй его так, чтобы он был важен для тебя 🤍"
    )
    
    return TAROT_QUESTION


async def tarot_question_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive tarot question and ask for card count"""
    question = update.message.text
    context.user_data['tarot_question'] = question
    
    keyboard = [
        [InlineKeyboardButton("1 карта — совет", callback_data="tarot_1card")],
        [InlineKeyboardButton("3 карты — прошлое / настоящее / будущее", callback_data="tarot_3cards")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Сколько карт вытянуть?",
        reply_markup=reply_markup
    )
    
    return TAROT_CARDS


async def tarot_draw_cards(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Draw cards and generate reading"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    question = context.user_data.get('tarot_question', '')
    
    # Determine spread type
    if query.data == "tarot_1card":
        spread_type = "1_card"
        num_cards = 1
    else:
        spread_type = "3_cards"
        num_cards = 3
    
    # Draw random cards
    deck = get_full_deck()
    cards = random.sample(deck, num_cards)
    
    await query.message.reply_text("Вытягиваю карты... ✨")
    
    # Generate reading
    reading = generate_tarot_reading(question, cards, spread_type)
    
    # Record usage
    UserDatabase.record_tarot(user_id)
    
    # Store in context for diary
    context.user_data['last_tarot_reading'] = reading
    
    # Buttons
    keyboard = [
        [InlineKeyboardButton("📝 Записать в дневник", callback_data="diary_save_tarot")],
        [InlineKeyboardButton("🔄 Ещё вопрос", callback_data="tarot")],
        [InlineKeyboardButton("⭐ Энергия дня", callback_data="daily_energy")]
    ]
    
    if UserDatabase.is_paid(user_id):
        keyboard.insert(1, [InlineKeyboardButton("🌿 Разобрать глубже", callback_data="deepen_tarot")])
    else:
        keyboard.insert(1, [InlineKeyboardButton("🌿 Разобрать глубже 🔒", callback_data="upgrade_needed")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(reading, reply_markup=reply_markup)
    
    return ConversationHandler.END


async def tarot_own_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start own deck tarot reading"""
    query = update.callback_query
    await query.answer()
    
    text = """🌿 У меня есть своя колода

Выбери расклад:"""
    
    keyboard = [
        [InlineKeyboardButton("1 карта — совет", callback_data="own_1card")],
        [InlineKeyboardButton("2 карты — ситуация", callback_data="own_2cards")],
        [InlineKeyboardButton("3 карты — прошлое / настоящее / будущее", callback_data="own_3cards")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(text, reply_markup=reply_markup)
    
    return OWN_DECK_QUESTION


async def own_deck_layout_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle own deck layout selection"""
    query = update.callback_query
    await query.answer()
    
    # Store layout type
    if query.data == "own_1card":
        context.user_data['own_deck_layout'] = "1_card"
        num_cards = 1
    elif query.data == "own_2cards":
        context.user_data['own_deck_layout'] = "2_cards"
        num_cards = 2
    else:
        context.user_data['own_deck_layout'] = "3_cards"
        num_cards = 3
    
    await query.message.reply_text(
        f"Достань {num_cards} карт{'у' if num_cards == 1 else 'ы' if num_cards < 5 else ''} из своей колоды.\n\n"
        "Сначала напиши свой вопрос:"
    )
    
    return OWN_DECK_QUESTION


async def own_deck_question_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive question for own deck"""
    question = update.message.text
    context.user_data['own_deck_question'] = question
    
    layout = context.user_data.get('own_deck_layout', '1_card')
    num_cards = int(layout[0])
    
    await update.message.reply_text(
        f"Теперь введи названия {num_cards} карт{'ы' if num_cards == 1 else ' карт'} через запятую:"
    )
    
    return OWN_DECK_CARDS


async def own_deck_cards_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and interpret own deck cards"""
    user_id = update.effective_user.id
    cards_text = update.message.text
    question = context.user_data.get('own_deck_question', '')
    layout = context.user_data.get('own_deck_layout', '1_card')
    
    # Parse cards
    cards = [card.strip() for card in cards_text.split(',')]
    
    await update.message.reply_text("Интерпретирую карты... ✨")
    
    # Generate reading
    reading = generate_own_deck_reading(question, cards, layout)
    
    # Store in context for diary
    context.user_data['last_tarot_reading'] = reading
    
    # Buttons
    keyboard = [
        [InlineKeyboardButton("📝 Записать в дневник", callback_data="diary_save_tarot")],
        [InlineKeyboardButton("🌿 Продолжить диалог", callback_data="continue_own_deck")],
        [InlineKeyboardButton("🔄 Новый расклад", callback_data="tarot_own")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(reading, reply_markup=reply_markup)
    
    return ConversationHandler.END


# ============================================
# DIARY FEATURE
# ============================================

async def diary_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show diary menu"""
    user_id = update.effective_user.id
    
    # Check if message or callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send_func = query.message.reply_text
    else:
        send_func = update.message.reply_text
    
    entry_count = DiaryDatabase.get_entry_count(user_id)
    
    text = f"""📝 Дневник

Это твои личные записи:
— вопросы
— ответы Таро
— мысли и ощущения

Всего записей: {entry_count}"""
    
    keyboard = [
        [InlineKeyboardButton("➕ Новая запись", callback_data="diary_new")],
        [InlineKeyboardButton("📖 Мои записи", callback_data="diary_view")]
    ]
    
    if UserDatabase.is_paid(user_id):
        keyboard.append([InlineKeyboardButton("🏷 Мои темы", callback_data="diary_themes")])
        keyboard.append([InlineKeyboardButton("📊 Мои паттерны", callback_data="diary_patterns")])
    else:
        keyboard.append([InlineKeyboardButton("🏷 Мои темы 🔒", callback_data="upgrade_needed")])
        keyboard.append([InlineKeyboardButton("📊 Мои паттерны 🔒", callback_data="upgrade_needed")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_func(text, reply_markup=reply_markup)


async def diary_new_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new diary entry"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "Напиши свои мысли, ощущения или всё, что хочешь сохранить 🤍"
    )
    
    return DIARY_ENTRY


async def diary_save_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save diary entry"""
    user_id = update.effective_user.id
    content = update.message.text
    
    DiaryDatabase.add_entry(user_id, content, "note")
    
    await update.message.reply_text(
        "Запись сохранена 🤍",
        reply_markup=get_main_menu()
    )
    
    return ConversationHandler.END


async def diary_save_daily_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save daily energy to diary"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    content = context.user_data.get('last_daily_energy', '')
    
    if content:
        DiaryDatabase.add_entry(user_id, content, "daily_energy")
        await query.answer("Энергия дня сохранена в дневник 🤍", show_alert=True)
    else:
        await query.answer("Нет данных для сохранения", show_alert=True)


async def diary_save_tarot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save tarot reading to diary"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    content = context.user_data.get('last_tarot_reading', '')
    
    if content:
        DiaryDatabase.add_entry(user_id, content, "tarot")
        await query.answer("Расклад Таро сохранён в дневник 🤍", show_alert=True)
    else:
        await query.answer("Нет данных для сохранения", show_alert=True)


async def diary_view_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View diary entries"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_paid = UserDatabase.is_paid(user_id)
    
    # Free users: last 5 entries, Paid users: all entries
    limit = None if is_paid else 5
    entries = DiaryDatabase.get_entries(user_id, limit)
    
    if not entries:
        await query.message.reply_text("У тебя пока нет записей в дневнике 🌿")
        return
    
    text = "📖 Твои записи:\n\n"
    
    for entry in entries[:5]:  # Show first 5
        date_str = entry['created_at'][:10]
        content_preview = entry['content'][:100] + "..." if len(entry['content']) > 100 else entry['content']
        text += f"📅 {date_str}\n{content_preview}\n\n"
    
    if not is_paid and len(entries) >= 5:
        text += "\n🔒 Оформи подписку для доступа ко всему архиву"
    
    await query.message.reply_text(text)


# ============================================
# NOTIFICATIONS FEATURE
# ============================================

async def notifications_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show notifications menu"""
    user_id = update.effective_user.id
    user = UserDatabase.get_user(user_id)
    
    # Check if message or callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send_func = query.message.reply_text
    else:
        send_func = update.message.reply_text
    
    daily_status = "✅" if user['notifications']['daily_energy'] else "⭕"
    diary_status = "✅" if user['notifications']['diary_reminder'] else "⭕"
    
    text = f"""🔔 Уведомления

{daily_status} Энергия дня — ежедневно
{diary_status} Напоминание записать мысли"""
    
    keyboard = [
        [InlineKeyboardButton("⭐ Энергия дня", callback_data="toggle_daily_notif")],
        [InlineKeyboardButton("📝 Напоминание о дневнике", callback_data="toggle_diary_notif")],
        [InlineKeyboardButton("❌ Отключить все", callback_data="disable_all_notif")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_func(text, reply_markup=reply_markup)


async def toggle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle notification settings"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = UserDatabase.get_user(user_id)
    
    if query.data == "toggle_daily_notif":
        user['notifications']['daily_energy'] = not user['notifications']['daily_energy']
        status = "включены" if user['notifications']['daily_energy'] else "выключены"
        await query.answer(f"Уведомления об энергии дня {status}", show_alert=True)
    elif query.data == "toggle_diary_notif":
        user['notifications']['diary_reminder'] = not user['notifications']['diary_reminder']
        status = "включены" if user['notifications']['diary_reminder'] else "выключены"
        await query.answer(f"Напоминания о дневнике {status}", show_alert=True)
    elif query.data == "disable_all_notif":
        user['notifications']['daily_energy'] = False
        user['notifications']['diary_reminder'] = False
        await query.answer("Все уведомления отключены", show_alert=True)
    
    UserDatabase.update_user(user_id, {"notifications": user['notifications']})
    
    # Refresh menu
    await notifications_menu(update, context)


# ============================================
# SUBSCRIPTION FEATURE
# ============================================

async def subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show subscription menu"""
    user_id = update.effective_user.id
    user = UserDatabase.get_user(user_id)
    
    # Check if message or callback
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        send_func = query.message.reply_text
    else:
        send_func = update.message.reply_text
    
    current_plan = user['subscription']
    
    text = f"""✨ Подписка

Текущий план: {current_plan.upper()}

Подписка — это пространство поддержки, а не просто функции 🤍

**BASE** (₽299/мес)
— больше раскладов Таро
— доступ к архиву
— углублённая энергия дня

**PREMIUM** (₽599/мес)
— всё из Base
— режим «Своя колода»
— глубокие интерпретации Таро
— темы и паттерны в дневнике"""
    
    keyboard = [
        [InlineKeyboardButton("🌿 Оформить BASE", callback_data="subscribe_base")],
        [InlineKeyboardButton("✨ Оформить PREMIUM", callback_data="subscribe_premium")]
    ]
    
    if current_plan != "free":
        keyboard.append([InlineKeyboardButton("❌ Отменить подписку", callback_data="cancel_subscription")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await send_func(text, reply_markup=reply_markup)


async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "subscribe_base":
        plan = "base"
        price = "₽299"
    else:
        plan = "premium"
        price = "₽599"
    
    # In production, integrate with payment system
    # For now, just show message
    await query.message.reply_text(
        f"Для оформления подписки {plan.upper()} ({price}/мес) свяжитесь с администратором.\n\n"
        "В реальной версии здесь будет интеграция с платёжной системой."
    )


async def upgrade_needed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show upgrade message"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "Эта функция доступна по подписке 🌿\n\n"
        "Оформи подписку, чтобы получить доступ к расширенным возможностям.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Посмотреть планы", callback_data="subscription")]
        ])
    )


async def upgrade_premium_needed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show premium upgrade message"""
    query = update.callback_query
    await query.answer()
    
    await query.message.reply_text(
        "Эта функция доступна только в PREMIUM подписке 🌿\n\n"
        "Оформи PREMIUM, чтобы использовать свою колоду и получить глубокие интерпретации.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Посмотреть планы", callback_data="subscription")]
        ])
    )


# ============================================
# DEEPENING FEATURES
# ============================================

async def deepen_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deepen interpretation for paid users"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not UserDatabase.is_paid(user_id):
        await upgrade_needed(update, context)
        return
    
    await query.message.reply_text("Создаю углублённую интерпретацию... ✨")
    
    # Get original content
    if query.data == "deepen_daily":
        original = context.user_data.get('last_daily_energy', '')
    else:  # deepen_tarot
        original = context.user_data.get('last_tarot_reading', '')
    
    if not original:
        await query.message.reply_text("Нет данных для углубления")
        return
    
    # Generate deeper interpretation
    deeper = generate_deeper_interpretation(original)
    
    await query.message.reply_text(deeper)


# ============================================
# MESSAGE HANDLERS
# ============================================

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages with menu buttons"""
    text = update.message.text
    
    if text == "⭐ Энергия дня":
        await daily_energy(update, context)
    elif text == "🃏 Таро":
        await tarot_menu(update, context)
    elif text == "📝 Дневник":
        await diary_menu(update, context)
    elif text == "🔔 Уведомления":
        await notifications_menu(update, context)
    elif text == "✨ Подписка":
        await subscription_menu(update, context)
    else:
        await update.message.reply_text(
            "Выбери действие из меню 🤍",
            reply_markup=get_main_menu()
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text(
        "Действие отменено 🤍",
        reply_markup=get_main_menu()
    )
    return ConversationHandler.END


# ============================================
# CALLBACK QUERY ROUTER
# ============================================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries"""
    query = update.callback_query
    
    if query.data == "daily_energy":
        await daily_energy(update, context)
    elif query.data == "tarot":
        await tarot_menu(update, context)
    elif query.data == "diary":
        await diary_menu(update, context)
    elif query.data == "how_it_works":
        await how_it_works(update, context)
    elif query.data == "diary_save_daily":
        await diary_save_daily_energy(update, context)
    elif query.data == "diary_save_tarot":
        await diary_save_tarot(update, context)
    elif query.data == "diary_view":
        await diary_view_entries(update, context)
    elif query.data == "notify_daily":
        await query.answer("Уведомления настроены! 🔔", show_alert=True)
    elif query.data.startswith("toggle_") or query.data == "disable_all_notif":
        await toggle_notification(update, context)
    elif query.data == "subscription":
        await subscription_menu(update, context)
    elif query.data.startswith("subscribe_"):
        await subscribe(update, context)
    elif query.data == "upgrade_needed":
        await upgrade_needed(update, context)
    elif query.data == "upgrade_premium":
        await upgrade_premium_needed(update, context)
    elif query.data.startswith("deepen_"):
        await deepen_content(update, context)


# ============================================
# MAIN FUNCTION
# ============================================

def main():
    """Start the bot"""
    # Get bot token from environment
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set")
        print("Please set it with: export TELEGRAM_BOT_TOKEN='your_token_here'")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    
    # Tarot conversation handler
    tarot_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(tarot_bot_start, pattern="^tarot_bot$"),
            CallbackQueryHandler(own_deck_layout_selected, pattern="^own_(1|2|3)cards$")
        ],
        states={
            TAROT_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, tarot_question_received)],
            TAROT_CARDS: [CallbackQueryHandler(tarot_draw_cards, pattern="^tarot_(1|3)card")],
            OWN_DECK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, own_deck_question_received)],
            OWN_DECK_CARDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, own_deck_cards_received)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(tarot_conv)
    
    # Diary conversation handler
    diary_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(diary_new_entry, pattern="^diary_new$")],
        states={
            DIARY_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, diary_save_entry)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    application.add_handler(diary_conv)
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(callback_router))
    
    # Text message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Start bot
    print("Bot started! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
