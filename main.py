import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import TELEGRAM_BOT_TOKEN, CITIES, MANAGER_CHAT_ID
from user_data import user_data
from datetime import datetime

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
