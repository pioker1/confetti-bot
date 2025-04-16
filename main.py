import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import (
    TELEGRAM_BOT_TOKEN, CITIES, MANAGER_CHAT_ID, EVENT_TYPES,
    CITY_CHANNELS, GENERAL_INFO, MANAGER_INFO, MANAGER_CONTACT_MESSAGES,
    LOCATION_PDF_FILES
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
CHOOSING_CITY, CHOOSING_EVENT_TYPE, CHOOSING_LOCATION = range(3)

# Кнопки
BACK_BUTTON = "⬅️ Назад"
CONTACT_MANAGER_BUTTON = "📞 Зв'язатися з менеджером"
SUGGEST_LOCATION_BUTTON = "🗺 Підказати вибір місця проведення"

# Локації для різних типів подій
LOCATIONS = {
    '🎂 День народження': [
        '🏠 Вдома',
        '🍽 Ресторан/Кафе',
        '🏫 Садочок/Школа',
        '🏰 Заміський комплекс',
        '📍 Інше'
    ],
    '🎓 Випускний': [
        '🍽 Ресторан/Кафе',
        '🏫 Садочок/Школа',
        '🏰 Заміський комплекс',
        '📍 Інше'
    ]
}

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

def create_location_keyboard(event_type: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру з локаціями для конкретного типу події"""
    locations = LOCATIONS.get(event_type, [])
    keyboard = []
    # Додаємо локації по 2 в рядок
    for i in range(0, len(locations), 2):
        row = [KeyboardButton(locations[i])]
        if i + 1 < len(locations):
            row.append(KeyboardButton(locations[i + 1]))
        keyboard.append(row)
    # Додаємо кнопку "Назад"
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_other_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру для розділу 'Інше'"""
    keyboard = [
        [KeyboardButton(SUGGEST_LOCATION_BUTTON)],
        [KeyboardButton(CONTACT_MANAGER_BUTTON)],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_manager_contact_message(city: str) -> str:
    """Формує повідомлення з контактами менеджера для конкретного міста"""
    manager = MANAGER_INFO[city]
    message_template = MANAGER_CONTACT_MESSAGES[city]
    return message_template.format(
        phone=manager['phone'],
        name=manager['name'],
        telegram=manager['telegram']
    )

def initialize_user_choices(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ініціалізує структуру для збереження виборів користувача"""
    if 'choices' not in context.user_data:
        context.user_data['choices'] = []

def add_choice(context: ContextTypes.DEFAULT_TYPE, choice_type: str, value: str) -> None:
    """Додає вибір користувача до історії"""
    initialize_user_choices(context)
    context.user_data['choices'].append({'type': choice_type, 'value': value})
    logger.info(f"Додано вибір: {choice_type} = {value}")

def remove_last_choice(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Видаляє та повертає останній вибір користувача"""
    initialize_user_choices(context)
    if context.user_data['choices']:
        last_choice = context.user_data['choices'].pop()
        logger.info(f"Видалено останній вибір: {last_choice}")
        return last_choice
    return None

def get_current_choices(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Формує текстове представлення поточних виборів користувача"""
    initialize_user_choices(context)
    if not context.user_data['choices']:
        return "Ще не зроблено жодного вибору"
    
    choices_text = "Ваші поточні вибори:\n"
    for choice in context.user_data['choices']:
        choices_text += f"• {choice['type']}: {choice['value']}\n"
    return choices_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Початок розмови та повернення до головного меню"""
    user = update.effective_user
    
    # Очищаємо стан розмови
    user_data.clear_conversation_state(user.id)
    
    # Зберігаємо базову інформацію про користувача
    user_info = {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'last_interaction': datetime.now().isoformat()
    }
    user_data.add_user(user.id, user_info)
    
    await update.message.reply_text(
        "🎉 Вітаємо у Confetti - вашому провіднику у світ незабутніх свят! "
        "Оберіть місто, де ви хочете організувати свято:",
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
    add_choice(context, "Місто", city)
    await save_state(update, context, CHOOSING_EVENT_TYPE)
    
    # Показуємо типи подій
    await update.message.reply_text(
        "Оберіть тип події:",
        reply_markup=create_event_type_keyboard()
    )
    
    return CHOOSING_EVENT_TYPE

async def event_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору типу події"""
    event_type = update.message.text
    
    if event_type == BACK_BUTTON:
        # Видаляємо останній вибір
        last_choice = remove_last_choice(context)
        if last_choice:
            if last_choice['type'] == "Місто":
                await save_state(update, context, CHOOSING_CITY)
                await update.message.reply_text(
                    "Оберіть місто, де відбудеться подія:",
                    reply_markup=create_city_keyboard()
                )
                return CHOOSING_CITY
            else:
                await save_state(update, context, CHOOSING_EVENT_TYPE)
                await update.message.reply_text(
                    "Оберіть тип події:",
                    reply_markup=create_event_type_keyboard()
                )
                return CHOOSING_EVENT_TYPE
    
    if event_type == CONTACT_MANAGER_BUTTON:
        # Показуємо контакти менеджера
        city = next((choice['value'] for choice in context.user_data['choices'] 
                    if choice['type'] == "Місто"), None)
        await update.message.reply_text(
            get_manager_contact_message(city),
            reply_markup=create_other_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    if event_type == SUGGEST_LOCATION_BUTTON:
        # Відправляємо PDF файл з підказками щодо місць проведення
        city = next((choice['value'] for choice in context.user_data['choices'] 
                    if choice['type'] == "Місто"), None)
        pdf_path = LOCATION_PDF_FILES.get(city)
        try:
            with open(pdf_path, 'rb') as file:
                await update.message.reply_document(
                    document=file,
                    caption=f"📍 Підказки щодо місць проведення у місті {city}",
                    reply_markup=create_other_keyboard()
                )
        except FileNotFoundError:
            await update.message.reply_text(
                "На жаль, файл з підказками тимчасово недоступний. "
                "Будь ласка, зв'яжіться з менеджером для отримання інформації.",
                reply_markup=create_other_keyboard()
            )
        return CHOOSING_EVENT_TYPE
    
    if event_type not in EVENT_TYPES:
        await update.message.reply_text(
            "Будь ласка, оберіть тип події зі списку:",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    # Зберігаємо вибір типу події
    add_choice(context, "Тип події", event_type)
    
    # Обробка спеціальних гілок
    if '📅 Афіша подій' in event_type:
        city = next((choice['value'] for choice in context.user_data['choices'] 
                    if choice['type'] == "Місто"), None)
        channel_link = CITY_CHANNELS[city]
        await update.message.reply_text(
            f"📅 Афіша подій у місті {city}\n"
            f"Підписуйтесь на наш канал, щоб бути в курсі всіх подій:\n"
            f"{channel_link}",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    elif '🎯 Інше' in event_type:
        city = next((choice['value'] for choice in context.user_data['choices'] 
                    if choice['type'] == "Місто"), None)
        # Зберігаємо вибір типу події
        add_choice(context, "Тип події", event_type)
        
        # Показуємо загальну інформацію та клавіатуру з опціями
        await update.message.reply_text(
            f"{GENERAL_INFO[city]}\n\n"
            "Оберіть опцію:",
            reply_markup=create_other_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    # Для Дня народження та Випускного показуємо вибір локації
    elif '🎂 День народження' in event_type or '🎓 Випускний' in event_type:
        await save_state(update, context, CHOOSING_LOCATION)
        await update.message.reply_text(
            "Оберіть локацію для події:",
            reply_markup=create_location_keyboard(event_type)
        )
        return CHOOSING_LOCATION
    
    # Для інших типів подій
    await update.message.reply_text(
        "Наступний крок буде додано незабаром..."
    )
    
    return ConversationHandler.END

async def location_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору локації"""
    location = update.message.text
    event_type = next((choice['value'] for choice in context.user_data['choices'] 
                      if choice['type'] == "Тип події"), None)
    
    if location == BACK_BUTTON:
        # Видаляємо останній вибір
        remove_last_choice(context)
        await save_state(update, context, CHOOSING_EVENT_TYPE)
        await update.message.reply_text(
            "Оберіть тип події:",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    if event_type and location not in LOCATIONS.get(event_type, []):
        await update.message.reply_text(
            "Будь ласка, оберіть локацію зі списку:",
            reply_markup=create_location_keyboard(event_type)
        )
        return CHOOSING_LOCATION
    
    # Зберігаємо вибір локації
    add_choice(context, "Локація", location)
    await save_state(update, context, CHOOSING_LOCATION)
    
    # Тут буде додано наступний крок (буде реалізовано пізніше)
    await update.message.reply_text(
        "Дякуємо за вибір локації! Наступний крок буде додано незабаром..."
    )
    
    return ConversationHandler.END

async def save_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: int) -> None:
    """Зберігає поточний стан розмови"""
    if user_data and update.effective_user:
        state_data = {
            'choices': context.user_data.get('choices', []),
            'last_state': state,
            'last_update': datetime.now().isoformat()
        }
        user_data.save_conversation_state(update.effective_user.id, state_data)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасування розмови"""
    if user_data and update.effective_user:
        user_data.clear_conversation_state(update.effective_user.id)
    
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
            CHOOSING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_chosen)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main() 
