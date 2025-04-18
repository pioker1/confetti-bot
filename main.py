import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import (
    TELEGRAM_BOT_TOKEN, CITIES, EVENT_TYPES,
    CITY_CHANNELS, GENERAL_INFO, MANAGER_INFO, MANAGER_CONTACT_MESSAGES,
    LOCATION_PDF_FILES, LOCATIONS, LOCATION_INFO, THEMES, THEME_INFO, THEME_BTN
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
CHOOSING_CITY, CHOOSING_EVENT_TYPE, CHOOSING_LOCATION, CHOOSING_THEME = range(4)

# Кнопки
BACK_BUTTON = "⬅️ Назад"
CONTACT_MANAGER_BUTTON = "📞 Зв'язатися з менеджером"
SUGGEST_LOCATION_BUTTON = "🗺 Підказати вибір місця проведення"

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

def create_theme_keyboard(context: ContextTypes.DEFAULT_TYPE = None) -> ReplyKeyboardMarkup:
    """Створює клавіатуру з тематиками свят"""
    keyboard = []
    
    # Якщо передано контекст, перевіряємо чи є вже вибрана тематика
    if context and 'choices' in context.user_data:
        # Шукаємо останню вибрану тематику
        theme_choice = next((choice for choice in reversed(context.user_data['choices']) 
                           if choice['type'] == "Тематика"), None)
        
        if theme_choice and theme_choice['value'] in THEME_BTN:
            # Якщо тематика вибрана, показуємо підтеми
            subthemes = THEME_BTN[theme_choice['value']]
            # Додаємо підтеми по 2 в рядок
            for i in range(0, len(subthemes), 2):
                row = [KeyboardButton(subthemes[i])]
                if i + 1 < len(subthemes):
                    row.append(KeyboardButton(subthemes[i + 1]))
                keyboard.append(row)
        else:
            # Якщо тематика не вибрана або не має підтем, показуємо основні тематики
            for i in range(0, len(THEMES) - 1, 2):  # -1 щоб не включати "Зв'язатись з менеджером" в пари
                row = [KeyboardButton(THEMES[i])]
                if i + 1 < len(THEMES) - 1:  # -1 з тієї ж причини
                    row.append(KeyboardButton(THEMES[i + 1]))
                keyboard.append(row)
    else:
        # Якщо контекст не передано, показуємо основні тематики
        for i in range(0, len(THEMES) - 1, 2):
            row = [KeyboardButton(THEMES[i])]
            if i + 1 < len(THEMES) - 1:
                row.append(KeyboardButton(THEMES[i + 1]))
            keyboard.append(row)
    
    # Додаємо "Зв'язатись з менеджером" окремим рядком
    keyboard.append([KeyboardButton(THEMES[-1])])
    # Додаємо кнопку "Назад"
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_choise_theme_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру обраній темі"""
    keyboard = []
    for i in range(0, len(THEME_BTN[theme]) - 1, 2):
        row = [KeyboardButton(THEME_BTN[theme][i])]
        if i + 1 < len(THEME_BTN[theme]) - 1:
            row.append(KeyboardButton(THEME_BTN[theme][i + 1]))
        keyboard.append(row)
    keyboard.append([KeyboardButton(BACK_BUTTON)])
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
        city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                    if choice['type'] == "Місто"), None)
        if not city:
            await update.message.reply_text(
                "Спочатку оберіть місто:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
            
        await update.message.reply_text(
            get_manager_contact_message(city),
            reply_markup=create_other_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    if event_type == SUGGEST_LOCATION_BUTTON:
        # Відправляємо PDF файл з підказками щодо місць проведення
        city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                    if choice['type'] == "Місто"), None)
        if not city:
            await update.message.reply_text(
                "Спочатку оберіть місто:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
            
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
        city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                    if choice['type'] == "Місто"), None)
        if not city:
            await update.message.reply_text(
                "Спочатку оберіть місто:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
            
        channel_link = CITY_CHANNELS[city]
        await update.message.reply_text(
            f"📅 Афіша подій у місті {city}\n"
            f"Підписуйтесь на наш канал, щоб бути в курсі всіх подій:\n"
            f"{channel_link}",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    elif '🎯 Інше' in event_type:
        city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                    if choice['type'] == "Місто"), None)
        if not city:
            await update.message.reply_text(
                "Спочатку оберіть місто:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
            
        await update.message.reply_text(
            GENERAL_INFO[city],
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
    event_type = next((choice['value'] for choice in context.user_data.get('choices', []) 
                      if choice['type'] == "Тип події"), None)
    city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                if choice['type'] == "Місто"), None)
    
    if location == BACK_BUTTON:
        # Видаляємо останній вибір
        last_choice = remove_last_choice(context)
        if last_choice:
            if last_choice['type'] == "Тип події":
                await save_state(update, context, CHOOSING_EVENT_TYPE)
                await update.message.reply_text(
                    "Оберіть тип події:",
                    reply_markup=create_event_type_keyboard()
                )
                return CHOOSING_EVENT_TYPE
            else:
                await save_state(update, context, CHOOSING_LOCATION)
                await update.message.reply_text(
                    "Оберіть локацію для події:",
                    reply_markup=create_location_keyboard(event_type)
                )
                return CHOOSING_LOCATION
    
    if event_type and location not in LOCATIONS.get(event_type, []):
        await update.message.reply_text(
            "Будь ласка, оберіть локацію зі списку:",
            reply_markup=create_location_keyboard(event_type)
        )
        return CHOOSING_LOCATION
    
    # Зберігаємо вибір локації
    add_choice(context, "Локація", location)
    await save_state(update, context, CHOOSING_THEME)
    
    # Якщо обрано "Інше", показуємо додаткові опції
    if location == '📍 Інше':
        await update.message.reply_text(
            f"{LOCATION_INFO[city][location]}\n\n"
            "Оберіть опцію:",
            reply_markup=create_other_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
    # Для всіх інших локацій переходимо до вибору тематики
    await update.message.reply_text(
        "Оберіть тематику свята:",
        reply_markup=create_theme_keyboard(context)
    )
    
    return CHOOSING_THEME

async def theme_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору тематики"""
    theme = update.message.text
    
    if theme == BACK_BUTTON:
        # Видаляємо останній вибір
        last_choice = remove_last_choice(context)
        if last_choice:
            if last_choice['type'] == "Локація":
                await save_state(update, context, CHOOSING_LOCATION)
                event_type = next((choice['value'] for choice in context.user_data.get('choices', []) 
                                if choice['type'] == "Тип події"), None)
                await update.message.reply_text(
                    "Оберіть локацію для події:",
                    reply_markup=create_location_keyboard(event_type)
                )
                return CHOOSING_LOCATION
            elif last_choice['type'] == "Підтема":
                # Якщо була вибрана підтема, повертаємося до вибору підтем
                await save_state(update, context, CHOOSING_THEME)
                await update.message.reply_text(
                    "Оберіть підтему:",
                    reply_markup=create_theme_keyboard(context)
                )
                return CHOOSING_THEME
            elif last_choice['type'] == "Тематика":
                # Якщо була вибрана основна тематика, повертаємося до вибору локації
                await save_state(update, context, CHOOSING_LOCATION)
                event_type = next((choice['value'] for choice in context.user_data.get('choices', []) 
                                if choice['type'] == "Тип події"), None)
                await update.message.reply_text(
                    "Оберіть локацію для події:",
                    reply_markup=create_location_keyboard(event_type)
                )
                return CHOOSING_LOCATION
    
    if theme == '📞 Зв\'язатись з менеджером':
        city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                    if choice['type'] == "Місто"), None)
        if not city:
            await update.message.reply_text(
                "Спочатку оберіть місто:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
            
        await update.message.reply_text(
            get_manager_contact_message(city),
            reply_markup=create_theme_keyboard(context)
        )
        return CHOOSING_THEME
    
    # Перевіряємо, чи це підтема
    theme_choice = next((choice for choice in reversed(context.user_data.get('choices', [])) 
                        if choice['type'] == "Тематика"), None)
    
    if theme_choice and theme_choice['value'] in THEME_BTN and theme in THEME_BTN[theme_choice['value']]:
        # Якщо це підтема, зберігаємо її
        add_choice(context, "Підтема", theme)
        
        # Показуємо опис обраної підтеми та завершуємо розмову
        await update.message.reply_text(
            f"✨ {theme_choice['value']} - {theme}\n\n"
            f"Наш менеджер зв'яжеться з вами найближчим часом для уточнення деталей!"
        )
        return ConversationHandler.END
    
    # Якщо це основна тематика
    if theme in THEMES:
        # Зберігаємо вибір тематики
        add_choice(context, "Тематика", theme)
        
        if theme in THEME_BTN:
            # Якщо у тематики є підтеми, показуємо їх
            await update.message.reply_text(
                f"Оберіть підтему для {theme}:",
                reply_markup=create_theme_keyboard(context)
            )
            return CHOOSING_THEME
        else:
            # Якщо підтем немає, завершуємо розмову
            await update.message.reply_text(
                f"✨ {theme}\n\n"
                f"{THEME_INFO[theme]}\n\n"
                "Наш менеджер зв'яжеться з вами найближчим часом для уточнення деталей!"
            )
            return ConversationHandler.END
    
    await update.message.reply_text(
        "Будь ласка, оберіть тематику зі списку:",
        reply_markup=create_theme_keyboard(context)
    )
    return CHOOSING_THEME

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
            CHOOSING_THEME: [MessageHandler(filters.TEXT & ~filters.COMMAND, theme_chosen)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main() 
