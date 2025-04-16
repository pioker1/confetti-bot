import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import (
    TELEGRAM_BOT_TOKEN, CITIES, MANAGER_CHAT_ID, EVENT_TYPES,
    CITY_CHANNELS, GENERAL_INFO, MANAGER_INFO
)
from user_data import user_data
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Стани розмови
CHOOSING_CITY, CHOOSING_EVENT_TYPE = range(2)

# Кнопки
BACK_BUTTON = "⬅️ Назад"
CONTACT_MANAGER_BUTTON = "📞 Зв'язатися з менеджером"

def create_city_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру з доступними містами"""
    keyboard = [[KeyboardButton(city)] for city in CITIES]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def create_event_type_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру з типами подій"""
    keyboard = []
    # Додаємо типи подій по 2 в рядок
    for i in range(0, len(EVENT_TYPES), 2):
        row = [KeyboardButton(EVENT_TYPES[i])]
        if i + 1 < len(EVENT_TYPES):
            row.append(KeyboardButton(EVENT_TYPES[i + 1]))
        keyboard.append(row)
    # Додаємо кнопку "Назад" в останній рядок
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_other_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру для розділу 'Інше'"""
    keyboard = [
        [KeyboardButton(CONTACT_MANAGER_BUTTON)],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка команди /start"""
    user = update.effective_user
    user_id = user.id
    
    # Перевіряємо наявність user_data
    if user_data is None:
        logger.error("Помилка: user_data не ініціалізовано")
        await update.message.reply_text(
            "На жаль, зараз виникли технічні проблеми. Будь ласка, спробуйте пізніше."
        )
        return ConversationHandler.END
    
    # Перевіряємо, чи користувач вже існує
    existing_user = user_data.get_user(user_id)
    if not existing_user:
        # Створюємо нового користувача
        user_info = {
            'user_id': user_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'created_at': datetime.now().isoformat()
        }
        user_data.add_user(user_id, user_info)
        logger.info(f"Створено нового користувача: {user_id}")
        
        # Відправляємо повідомлення менеджеру про нового користувача
        if MANAGER_CHAT_ID:
            try:
                await context.bot.send_message(
                    chat_id=MANAGER_CHAT_ID,
                    text=f"🆕 Новий користувач:\n"
                         f"ID: {user_id}\n"
                         f"Username: @{user.username if user.username else 'немає'}\n"
                         f"Ім'я: {user.first_name} {user.last_name if user.last_name else ''}"
                )
            except Exception as e:
                logger.error(f"Помилка при відправці повідомлення менеджеру: {e}")
    
    # Очищаємо попередні дані користувача
    context.user_data.clear()
    
    # Відправляємо привітання
    await update.message.reply_text(
        "Вітаємо! 👋\n"
        "Я бот для замовлення послуг аніматора.\n"
        "Оберіть місто, де відбудеться подія:",
        reply_markup=create_city_keyboard()
    )
    
    return CHOOSING_CITY

async def city_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору міста"""
    city = update.message.text
    
    if city not in CITIES:
        await update.message.reply_text(
            "Будь ласка, оберіть місто зі списку:",
            reply_markup=create_city_keyboard()
        )
        return CHOOSING_CITY
    
    # Зберігаємо вибір міста
    context.user_data['city'] = city
    
    # Показуємо типи подій
    await update.message.reply_text(
        f"🏙 Ви обрали місто: {city}\n"
        "Тепер оберіть тип події:",
        reply_markup=create_event_type_keyboard()
    )
    
    return CHOOSING_EVENT_TYPE

async def event_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору типу події"""
    event_type = update.message.text
    city = context.user_data.get('city')
    
    if event_type == BACK_BUTTON:
        # Повертаємося до вибору міста
        await update.message.reply_text(
            "Оберіть місто, де відбудеться подія:",
            reply_markup=create_city_keyboard()
        )
        return CHOOSING_CITY
    
    if event_type == CONTACT_MANAGER_BUTTON:
        # Показуємо контакти менеджера
        manager = MANAGER_INFO[city]
        await update.message.reply_text(
            f"📞 Контакти менеджера ({city}):\n\n"
            f"Ім'я: {manager['name']}\n"
            f"Телефон: {manager['phone']}\n"
            f"Telegram: {manager['telegram']}"
        )
        # Залишаємося в поточному стані
        return CHOOSING_EVENT_TYPE
    
    if event_type not in EVENT_TYPES:
        await update.message.reply_text(
            "Будь ласка, оберіть тип події зі списку:",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    # Зберігаємо вибір типу події
    context.user_data['event_type'] = event_type
    
    # Обробка спеціальних гілок
    if '📅 Афіша подій' in event_type:
        channel_link = CITY_CHANNELS[city]
        await update.message.reply_text(
            f"📅 Афіша подій у місті {city}\n\n"
            f"Підписуйтесь на наш канал, щоб бути в курсі всіх подій:\n"
            f"{channel_link}",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    elif '🎯 Інше' in event_type:
        # Показуємо загальну інформацію та кнопку для зв'язку з менеджером
        await update.message.reply_text(
            GENERAL_INFO[city],
            reply_markup=create_other_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    # Тут буде обробка інших типів подій (буде додано пізніше)
    await update.message.reply_text(
        f"🎉 Ви обрали: {event_type}\n"
        "Наступний крок буде додано незабаром..."
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасування розмови"""
    await update.message.reply_text(
        'Розмову скасовано. Щоб почати спочатку, використайте команду /start'
    )
    return ConversationHandler.END

def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Налаштування обробника розмови
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_chosen)],
            CHOOSING_EVENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_type_chosen)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main() 
