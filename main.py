import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_BOT_TOKEN, CITIES
from user_data import user_data

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Стани розмови
MAIN_MENU, CHOOSING_CITY = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка команди /start"""
    user = update.effective_user
    
    # Збираємо інформацію про користувача
    user_info = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'username': user.username,
        'language_code': user.language_code,
        'last_visit': update.message.date.strftime("%Y-%m-%d %H:%M:%S"),
        'registration_date': update.message.date.strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'Активний'
    }
    
    # Зберігаємо інформацію про користувача
    user_data.add_user(str(user.id), user_info)
    
    # Відправляємо привітання
    await update.message.reply_text(
        f"Вітаю, {user.first_name}! 🎉\n"
        "Я допоможу вам організувати незабутнє свято!\n\n"
        "Оберіть місто, де буде проходити свято:"
    )
    
    # Створюємо клавіатуру з містами
    keyboard = [[KeyboardButton(city)] for city in CITIES]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "Оберіть місто:",
        reply_markup=reply_markup
    )
    
    return CHOOSING_CITY

async def city_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору міста"""
    city = update.message.text
    
    if city not in CITIES:
        await update.message.reply_text(
            "Будь ласка, оберіть місто зі списку:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(city)] for city in CITIES],
                resize_keyboard=True
            )
        )
        return CHOOSING_CITY
    
    # Зберігаємо вибір міста
    user_id = str(update.effective_user.id)
    user_data.update_user(user_id, {'city': city})
    
    await update.message.reply_text(
        f"Чудово! Ви обрали місто {city}.\n"
        "Скоро ми додамо нові функції для продовження оформлення замовлення."
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
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main() 
