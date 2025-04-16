import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackContext
from config import (
    TELEGRAM_BOT_TOKEN, MANAGER_CHAT_ID, CITIES, EVENT_TYPES, LOCATIONS, 
    DURATIONS, ADDITIONAL_SERVICES, BASE_PRICES, DURATION_MULTIPLIERS,
    MANAGER_INFO, TAXI_PRICES, TAXI_PRICE_DISCLAIMER
)
from user_data import user_data
from datetime import datetime
import pandas as pd
import telegram

# Налаштування логування для відстеження роботи бота
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Стани розмови для керування діалогом з користувачем
# Кожен стан відповідає певному етапу взаємодії
MAIN_MENU, CONTACT_MANAGER, SERVICES_INFO, VIEWING_SERVICE = range(4)
(CHOOSING_CITY, CHOOSING_EVENT_TYPE, CHOOSING_LOCATION, 
 CHOOSING_DURATION, CHOOSING_SERVICES, ENTERING_CUSTOM_DURATION,
 WRITING_FEEDBACK, WRITING_COMPLAINT, WRITING_COMMENT,
 CHOOSING_DISTRICT, CONFIRM_ORDER) = range(4, 15)

# Опції головного меню з відповідними емодзі
MAIN_MENU_OPTIONS = {
    'contact_manager': '👩‍💼 Зв\'язатись з менеджером',
    'services_info': '📝 Дізнатись про послуги',
    'make_order': '🎉 Зробити замовлення'
}


# Детальний опис послуг з зображеннями та описом
SERVICE_DETAILS = {
    'День народження': {
        'description': '🎂 Організація незабутнього дня народження для дітей та дорослих. Включає:\n'
                      '• Аніматорів\n'
                      '• Розважальну програму\n'
                      '• Тематичне оформлення\n'
                      '• Смачний торт',
        'image': 'images/1.png'  # Шлях до локального файлу
    },
    'Випускний': {
        'description': '🎓 Організація випускного вечора для школярів та студентів. Включає:\n'
                      '• Торжественну частину\n'
                      '• Розважальну програму\n'
                      '• Фотосесію\n'
                      '• Пам\'ятні подарунки',
        'image': 'images/1.png'  # Шлях до локального файлу
    },
    'Корпоратив': {
        'description': '💼 Організація корпоративних заходів. Включає:\n'
                      '• Тимбілдинг\n'
                      '• Розважальну програму\n'
                      '• Кейтеринг\n'
                      '• Презентаційне обладнання',
        'image': 'images/1.png'  # Шлях до локального файлу
    }
}

def calculate_total_price(location, duration, services, city=None, district=None):
    """
    Розрахунок загальної вартості замовлення
    
    Args:
        location (str): Обрана локація
        duration (str): Обрана тривалість
        services (list): Список обраних додаткових послуг
        city (str, optional): Місто для розрахунку вартості таксі
        district (str, optional): Район для розрахунку вартості таксі
        
    Returns:
        tuple: (Загальна вартість замовлення, Вартість таксі)
    """
    try:
        # Базова ціна за локацію
        base_price = BASE_PRICES.get(location, 1500)
        
        # Множник за тривалість
        duration_multiplier = DURATION_MULTIPLIERS.get(duration, 1)
        
        # Розрахунок базової вартості
        total = base_price * duration_multiplier
        
        # Додавання вартості додаткових послуг
        if services:  # Перевірка на None та пустий список
            for service in services:
                service_info = ADDITIONAL_SERVICES.get(service)
                if service_info and 'price' in service_info:
                    total += service_info['price']
        
        # Розрахунок вартості таксі
        taxi_price = 0
        if city and district and city in TAXI_PRICES:
            city_taxi_prices = TAXI_PRICES[city]
            taxi_price = city_taxi_prices.get(district, city_taxi_prices.get('Інше', 0))
        
        return total, taxi_price
    except Exception as e:
        logger.error(f"Помилка при розрахунку вартості: {str(e)}")
        return 0, 0  # Повертаємо нульову вартість у разі помилки

def format_price_info(location, duration, services, city=None, district=None):
    """
    Форматування інформації про ціни для відображення користувачу
    
    Args:
        location (str): Обрана локація
        duration (str): Обрана тривалість
        services (list): Список обраних додаткових послуг
        city (str, optional): Місто для розрахунку вартості таксі
        district (str, optional): Район для розрахунку вартості таксі
        
    Returns:
        str: Відформатований текст з інформацією про ціни
    """
    try:
        # Розрахунок базової вартості
        base_price = BASE_PRICES.get(location, 1500)
        duration_multiplier = DURATION_MULTIPLIERS.get(duration, 1)
        base_total = base_price * duration_multiplier
        
        # Формування базової інформації
        info = (
            f"💰 Розрахунок вартості:\n\n"
            f"Базова вартість ({location}): {base_price} грн\n"
            f"Тривалість ({duration}): x{duration_multiplier}\n"
            f"Базова вартість з урахуванням часу: {base_total} грн\n\n"
        )
        
        # Розрахунок вартості додаткових послуг
        services_total = 0
        if services:
            info += "Додаткові послуги:\n"
            for service in services:
                service_info = ADDITIONAL_SERVICES.get(service)
                if service_info and 'price' in service_info:
                    price = service_info['price']
                    services_total += price
                    info += f"• {service}: {price} грн\n"
            info += f"\nВартість додаткових послуг: {services_total} грн\n"
        
        # Загальна вартість послуг
        total_services = base_total + services_total
        info += f"Загальна вартість послуг: {total_services} грн\n"
        
        # Розрахунок вартості таксі
        if city and district:
            city_taxi_prices = TAXI_PRICES.get(city, {})
            taxi_price = city_taxi_prices.get(district, city_taxi_prices.get('Інше', 0))
            
            if taxi_price:
                info += f"\n🚕 Вартість таксі (туди/назад): {taxi_price} грн\n"
                info += f"Загальна вартість з таксі: {total_services + taxi_price} грн\n\n"
                info += TAXI_PRICE_DISCLAIMER
        
        return info
    except Exception as e:
        logger.error(f"Помилка при форматуванні інформації про ціни: {str(e)}")
        return "Виникла помилка при розрахунку вартості. Будь ласка, спробуйте ще раз."

async def send_to_manager(context: ContextTypes.DEFAULT_TYPE, user_info: dict, message: str):
    """
    Відправка повідомлення менеджеру про нове замовлення
    
    Args:
        context: Контекст бота
        user_info (dict): Інформація про користувача
        message (str): Текст повідомлення
    """
    try:
        user = user_info['user']
        user_info_text = (
            f"👤 Нове замовлення від клієнта:\n"
            f"ID: {user.id}\n"
            f"Ім'я: {user.first_name}"
        )
        if user.last_name:
            user_info_text += f" {user.last_name}"
        if user.username:
            user_info_text += f"\nUsername: @{user.username}"
            
        full_message = f"{user_info_text}\n\n{message}"
        
        logger.info(f"Спроба відправити повідомлення менеджеру (ID: {MANAGER_CHAT_ID})")
        logger.info(f"Повідомлення: {full_message}")
        
        await context.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=full_message,
            parse_mode='HTML'
        )
        logger.info("Повідомлення успішно відправлено менеджеру")
        
    except Exception as e:
        logger.error(f"Помилка при відправці повідомлення менеджеру: {str(e)}")
        await context.bot.send_message(
            chat_id=user.id,
            text="Виникла помилка при відправці замовлення менеджеру. Будь ласка, спробуйте ще раз або зв'яжіться з нами іншим способом."
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показ головного меню з основними опціями
    
    Returns:
        int: Стан MAIN_MENU
    """
    keyboard = [
        [KeyboardButton(MAIN_MENU_OPTIONS['contact_manager'])],
        [KeyboardButton(MAIN_MENU_OPTIONS['services_info'])],
        [KeyboardButton(MAIN_MENU_OPTIONS['make_order'])]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        'Оберіть, будь ласка, що вас цікавить:',
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def contact_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка запиту на зв'язок з менеджером
    
    Returns:
        int: Стан CONTACT_MANAGER
    """
    keyboard = [
        [KeyboardButton('✍️ Написати відгук')],
        [KeyboardButton('⚠️ Написати скаргу')],
        [KeyboardButton('💬 Написати коментар')],
        [KeyboardButton('⬅️ Головне меню')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message = (
        f"👋 Вас вітає підтримка Confetti bot, оберіть метод зв'язку з менеджером\n\n"
        f"📱 Телефон: {MANAGER_INFO['phone']}\n"
        f"📨 Telegram: {MANAGER_INFO['telegram']}\n\n"
        "Час роботи: 10:00 - 20:00\n"
        "Або оберіть опцію з меню нижче"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup)
    return CONTACT_MANAGER

async def handle_manager_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору опції зв'язку з менеджером
    
    Returns:
        int: Відповідний стан розмови
    """
    choice = update.message.text
    
    if choice == '⬅️ Головне меню':
        return await show_main_menu(update, context)
    
    if choice == '✍️ Написати відгук':
        context.user_data['feedback_type'] = 'ВІДГУК'
        await update.message.reply_text(
            "Будь ласка, напишіть ваш відгук. Він буде надіслано менеджеру."
        )
        return WRITING_FEEDBACK
    
    if choice == '⚠️ Написати скаргу':
        context.user_data['feedback_type'] = 'СКАРГА'
        await update.message.reply_text(
            "Будь ласка, опишіть вашу скаргу. Вона буде надіслана менеджеру."
        )
        return WRITING_COMPLAINT
    
    if choice == '💬 Написати коментар':
        context.user_data['feedback_type'] = 'КОМЕНТАР'
        await update.message.reply_text(
            "Будь ласка, напишіть ваш коментар. Він буде надіслано менеджеру."
        )
        return WRITING_COMMENT
    
    return CONTACT_MANAGER

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка відгуку/скарги/коментаря користувача
    
    Returns:
        int: Стан MAIN_MENU
    """
    feedback_type = context.user_data.get('feedback_type', 'повідомлення')
    user = update.effective_user
    message = update.message.text
    
    # Формування повідомлення для менеджера
    manager_message = (
        f"📨 Новий {feedback_type} від користувача:\n\n"
        f"👤 Інформація про користувача:\n"
        f"ID: {user.id}\n"
        f"Ім'я: {user.first_name}"
    )
    if user.last_name:
        manager_message += f" {user.last_name}"
    if user.username:
        manager_message += f"\nUsername: @{user.username}"
    
    manager_message += f"\n\n📝 {feedback_type.capitalize()}:\n{message}"
    
    # Визначення тексту підтвердження
    confirmation_text = {
        'ВІДГУК': "Дякуємо! Ваш відгук надіслано менеджеру.",
        'СКАРГА': "Дякуємо! Ваша скарга надіслана менеджеру.",
        'КОМЕНТАР': "Дякуємо! Ваш коментар надіслано менеджеру."
    }.get(feedback_type, f"Дякуємо! Ваш {feedback_type} надіслано менеджеру.")
    
    # Відправка повідомлення менеджеру
    try:
        await context.bot.send_message(
            chat_id=MANAGER_CHAT_ID,
            text=manager_message
        )
        await update.message.reply_text(
            f"{confirmation_text}\nВін зв'яжеться з вами найближчим часом."
        )
    except Exception as e:
        logger.error(f"Помилка при відправці {feedback_type}: {str(e)}")
        await update.message.reply_text(
            f"Виникла помилка при відправці {feedback_type}. "
            "Будь ласка, спробуйте пізніше."
        )
    
    # Повернення до головного меню
    return await show_main_menu(update, context)

async def services_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показ інформації про послуги та їх вартість
    
    Returns:
        int: Стан VIEWING_SERVICE
    """
    info_message = (
        "🎪 Наші послуги:\n\n"
        "🎭 Організація свят:\n"
    )
    
    # Додавання інформації про базові ціни
    info_message += "\n📍 Базові ціни за локаціями (за годину):\n"
    for location, price in BASE_PRICES.items():
        info_message += f"• {location}: {price} грн\n"
    
    # Додавання інформації про додаткові послуги
    info_message += "\n🎁 Додаткові послуги:\n"
    for service, info in ADDITIONAL_SERVICES.items():
        info_message += f"• {service}: {info['price']} грн\n"
    
    # Створення клавіатури з кнопками послуг
    keyboard = []
    for service in EVENT_TYPES:
        keyboard.append([KeyboardButton(service)])
    keyboard.append([KeyboardButton('⬅️ Головне меню')])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    info_message += (
        "\n\n💡 Для отримання детальної інформації про конкретну послугу, "
        "оберіть її з меню нижче:"
    )
    
    await update.message.reply_text(info_message, reply_markup=reply_markup)
    return VIEWING_SERVICE

async def show_service_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показ детального опису обраної послуги з зображенням
    
    Returns:
        int: Стан VIEWING_SERVICE або MAIN_MENU
    """
    service_name = update.message.text
    
    if service_name == '⬅️ Головне меню':
        return await show_main_menu(update, context)
    
    if service_name in EVENT_TYPES:  # Використовуємо EVENT_TYPES з config.py
        service = SERVICE_DETAILS.get(service_name, {
            'description': 'Опис послуги тимчасово недоступний',
            'image': 'images/1.png'
        })
        
        # Відправка зображення послуги
        try:
            image_path = service['image']
            if os.path.exists(image_path):
                with open(image_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=InputFile(photo)
                    )
            else:
                logger.warning(f"Зображення не знайдено: {image_path}")
                await update.message.reply_text(
                    "На жаль, зображення тимчасово недоступне. Спробуйте пізніше."
                )
        except Exception as e:
            logger.error(f"Помилка при відправці картинки: {str(e)}")
            await update.message.reply_text(
                "На жаль, виникла помилка при відправці зображення. Спробуйте пізніше."
            )
        
        # Відправка опису послуги
        await update.message.reply_text(
            f"🎯 {service_name}\n\n{service['description']}\n\n"
            "Для повернення до списку послуг, оберіть іншу послугу або натисніть '⬅️ Головне меню'"
        )
        return VIEWING_SERVICE
    
    return await services_info(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка команди /start - початок роботи з ботом
    
    Returns:
        int: Стан MAIN_MENU
    """
    user = update.effective_user
    
    try:
        # Перевірка чи користувач вже існує
        existing_user = user_data.get_user(user.id)
        is_new_user = existing_user is None
        
        # Оновлення даних користувача
        user_info = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'language_code': user.language_code,
            'last_visit': update.message.date.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if is_new_user:
            user_info['registration_date'] = update.message.date.strftime("%Y-%m-%d %H:%M:%S")
            user_info['orders'] = []
            user_info['status'] = 'Активний'
            # Очищення даних тільки для нового користувача
            context.user_data.clear()
        else:
            # Оновлюємо статус користувача, якщо він був заблокований
            user_info['status'] = 'Активний'
            # Зберігаємо попередні дані користувача
            if 'state' not in context.user_data:
                context.user_data['state'] = MAIN_MENU
        
        user_data.add_user(user.id, user_info)
        
        # Формування повідомлення про нового користувача або повернення
        if is_new_user:
            new_user_message = (
                f"🔔 Новий користувач почав роботу з ботом:\n\n"
                f"👤 Інформація про користувача:\n"
                f"ID: {user.id}\n"
                f"Ім'я: {user.first_name}"
            )
            if user.last_name:
                new_user_message += f" {user.last_name}"
            if user.username:
                new_user_message += f"\nUsername: @{user.username}"
            if user.language_code:
                new_user_message += f"\nМова: {user.language_code}"
            
            current_time = update.message.date.strftime("%Y-%m-%d %H:%M:%S")
            new_user_message += f"\n\n⏰ Час початку: {current_time}"
            
            # Відправка повідомлення менеджеру про нового користувача
            try:
                await context.bot.send_message(
                    chat_id=MANAGER_CHAT_ID,
                    text=new_user_message,
                    parse_mode='HTML'
                )
                logger.info(f"Відправлено повідомлення менеджеру про нового користувача: {user.id}")
            except Exception as e:
                logger.error(f"Помилка при відправці повідомлення про нового користувача: {str(e)}")
        else:
            # Логування повернення користувача
            logger.info(f"Користувач {user.id} повернувся до бота")
        
        # Збереження інформації про користувача
        context.user_data['user'] = user
        
        # Відправка привітання користувачу
        if is_new_user:
            await update.message.reply_text(
                f"Вітаю, {user.first_name}! 🎉\n"
                "Я допоможу вам організувати незабутнє свято!"
            )
        else:
            # Перевіряємо, чи є незавершене замовлення
            if 'location' in context.user_data:
                await update.message.reply_text(
                    f"Вітаю з поверненням, {user.first_name}! 🎉\n"
                    "Ви можете продовжити оформлення замовлення з того місця, де зупинилися."
                )
            else:
                await update.message.reply_text(
                    f"Вітаю з поверненням, {user.first_name}! 🎉\n"
                    "Я допоможу вам організувати незабутнє свято!"
                )
        
        return await show_main_menu(update, context)
        
    except Exception as e:
        logger.error(f"Помилка при обробці команди /start: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка при запуску бота. Будь ласка, спробуйте ще раз."
        )
        return ConversationHandler.END

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору в головному меню
    
    Returns:
        int: Відповідний стан розмови
    """
    choice = update.message.text
    
    if choice == MAIN_MENU_OPTIONS['contact_manager']:
        context.user_data['state'] = CONTACT_MANAGER
        return await contact_manager(update, context)
    elif choice == MAIN_MENU_OPTIONS['services_info']:
        context.user_data['state'] = SERVICES_INFO
        return await services_info(update, context)
    elif choice == MAIN_MENU_OPTIONS['make_order']:
        context.user_data['state'] = CHOOSING_CITY
        keyboard = [[KeyboardButton(city)] for city in CITIES]
        keyboard.append([KeyboardButton('⬅️ Головне меню')])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        
        await update.message.reply_text(
            'Чудово! Давайте оформимо ваше замовлення. Спочатку оберіть місто:',
            reply_markup=reply_markup
        )
        return CHOOSING_CITY
    
    return MAIN_MENU

async def city_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору міста та перехід до вибору типу події
    
    Returns:
        int: Стан CHOOSING_EVENT_TYPE або MAIN_MENU
    """
    if update.message.text == '⬅️ Головне меню':
        context.user_data['state'] = MAIN_MENU
        return await show_main_menu(update, context)
    
    context.user_data['city'] = update.message.text
    context.user_data['state'] = CHOOSING_EVENT_TYPE
    
    keyboard = [[KeyboardButton(event_type)] for event_type in EVENT_TYPES]
    keyboard.append([KeyboardButton('⬅️ Головне меню')])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        'Оберіть тип події:',
        reply_markup=reply_markup
    )
    return CHOOSING_EVENT_TYPE

async def event_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору типу події та перехід до вибору локації
    
    Returns:
        int: Стан CHOOSING_LOCATION або MAIN_MENU
    """
    if update.message.text == '⬅️ Головне меню':
        context.user_data['state'] = MAIN_MENU
        return await show_main_menu(update, context)
    
    context.user_data['event_type'] = update.message.text
    context.user_data['state'] = CHOOSING_LOCATION
    
    keyboard = [[KeyboardButton(location)] for location in LOCATIONS]
    keyboard.append([KeyboardButton('⬅️ Головне меню')])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        'Оберіть місце проведення:',
        reply_markup=reply_markup
    )
    return CHOOSING_LOCATION

async def location_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору локації та перехід до вибору тривалості
    
    Returns:
        int: Стан CHOOSING_DURATION або CHOOSING_EVENT_TYPE
    """
    if update.message.text == '⬅️ Головне меню':
        context.user_data['state'] = MAIN_MENU
        keyboard = [[KeyboardButton(event_type)] for event_type in EVENT_TYPES]
        keyboard.append([KeyboardButton('⬅️ Головне меню')])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text('Оберіть тип події:', reply_markup=reply_markup)
        return CHOOSING_EVENT_TYPE
    
    location = update.message.text
    context.user_data['location'] = location
    context.user_data['state'] = CHOOSING_DURATION
    
    # Визначення доступних тривалостей залежно від локації
    if 'Домой' in location or 'кафе' in location:
        durations = DURATIONS.get('Домой/кафе', ['3 години', '4 години', '5 годин'])
    elif 'Турбаза' in location:
        durations = DURATIONS.get('Турбаза', ['4 години', '5 годин', '6 годин'])
    elif 'Садик-школа' in location:
        durations = DURATIONS.get('Садик-школа', ['2 години', '3 години', '4 години'])
    else:
        durations = ['3 години', '4 години', '5 годин']  # Значення за замовчуванням
    
    keyboard = [[KeyboardButton(duration)] for duration in durations]
    keyboard.append([KeyboardButton('⬅️ Головне меню')])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    # Показ базової вартості для обраної локації
    base_price = BASE_PRICES.get(location, 1500)
    await update.message.reply_text(
        f'Базова вартість для локації "{location}": {base_price} грн/година\n\n'
        'Оберіть тривалість заходу:',
        reply_markup=reply_markup
    )
    return CHOOSING_DURATION

async def duration_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору тривалості та перехід до вибору додаткових послуг
    
    Returns:
        int: Стан CHOOSING_SERVICES або CHOOSING_LOCATION
    """
    if update.message.text == '⬅️ Головне меню':
        context.user_data['state'] = MAIN_MENU
        keyboard = [[KeyboardButton(location)] for location in LOCATIONS]
        keyboard.append([KeyboardButton('⬅️ Головне меню')])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text('Оберіть місце проведення:', reply_markup=reply_markup)
        return CHOOSING_LOCATION
    
    if update.message.text == 'більше':
        context.user_data['state'] = ENTERING_CUSTOM_DURATION
        await update.message.reply_text(
            "Будь ласка, введіть тривалість свята у форматі:\n"
            "• Час у годинах (наприклад: 4)\n"
            "• Час у годинах з половиною (наприклад: 4.5)\n\n"
            "Доступні значення:\n"
            "• 3.5 години\n"
            "• 4 години\n"
            "• 4.5 години\n"
            "• 5 годин\n"
            "• 5.5 годин\n"
            "• 6 годин\n"
            "• 6.5 годин\n"
            "• 7 годин\n"
            "• 7.5 годин\n"
            "• 8 годин\n"
            "• 8.5 годин\n"
            "• 9 годин\n"
            "• 9.5 годин\n"
            "• 10 годин\n"
            "• 10.5 годин\n"
            "• 11 годин\n"
            "• 11.5 годин\n"
            "• 12 годин"
        )
        return ENTERING_CUSTOM_DURATION
    
    context.user_data['duration'] = update.message.text
    context.user_data['state'] = CHOOSING_SERVICES
    
    # Створення клавіатури з додатковими послугами
    keyboard = []
    for service, info in ADDITIONAL_SERVICES.items():
        button_text = f"{service} ({info['price']} грн)"
        keyboard.append([KeyboardButton(button_text)])
    
    keyboard.append([KeyboardButton('❌ Видалити послугу')])
    keyboard.append([KeyboardButton('💰 Розрахувати вартість')])
    keyboard.append([KeyboardButton('✅ Завершити вибір')])
    keyboard.append([KeyboardButton('⬅️ Головне меню')])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    context.user_data['services'] = []
    
    # Показ базової вартості з урахуванням тривалості
    location = context.user_data.get('location')
    duration = context.user_data.get('duration')
    base_price = BASE_PRICES.get(location, 1500)
    duration_multiplier = DURATION_MULTIPLIERS.get(duration, 1)
    total = base_price * duration_multiplier
    
    await update.message.reply_text(
        f'Базова вартість: {total} грн\n\n'
        'Оберіть додаткові послуги (можна обрати декілька).\n'
        'Використовуйте кнопки:\n'
        '• ❌ Видалити послугу - для видалення послуги\n'
        '• 💰 Розрахувати вартість - для перегляду поточної вартості\n'
        '• ✅ Завершити вибір - для завершення замовлення',
        reply_markup=reply_markup
    )
    return CHOOSING_SERVICES

async def handle_custom_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка введення користувачем тривалості свята
    
    Returns:
        int: Стан CHOOSING_SERVICES або ENTERING_CUSTOM_DURATION
    """
    try:
        duration_text = update.message.text.strip()
        duration = float(duration_text)
        
        # Перевірка діапазону
        if duration < 3.5:
            await update.message.reply_text(
                "Тривалість не може бути менше 3.5 годин. Будь ласка, введіть коректне значення."
            )
            return ENTERING_CUSTOM_DURATION
        
        if duration > 12:
            await update.message.reply_text(
                "Тривалість не може бути більше 12 годин. Будь ласка, введіть коректне значення."
            )
            return ENTERING_CUSTOM_DURATION
        
        # Перевірка на кратність 0.5
        if not (duration * 2).is_integer():
            await update.message.reply_text(
                "Тривалість повинна бути кратною 0.5 години. "
                "Наприклад: 3.5, 4, 4.5, 5, 5.5 і т.д."
            )
            return ENTERING_CUSTOM_DURATION
        
        # Зберігаємо тривалість
        context.user_data['duration'] = f"{duration} годин"
        context.user_data['duration_multiplier'] = duration
        
        # Переходимо до вибору послуг
        context.user_data['state'] = CHOOSING_SERVICES
        
        # Створення клавіатури з додатковими послугами
        keyboard = []
        for service, info in ADDITIONAL_SERVICES.items():
            button_text = f"{service} ({info['price']} грн)"
            keyboard.append([KeyboardButton(button_text)])
        
        keyboard.append([KeyboardButton('❌ Видалити послугу')])
        keyboard.append([KeyboardButton('💰 Розрахувати вартість')])
        keyboard.append([KeyboardButton('✅ Завершити вибір')])
        keyboard.append([KeyboardButton('⬅️ Головне меню')])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        context.user_data['services'] = []
        
        # Показ базової вартості з урахуванням тривалості
        location = context.user_data.get('location')
        base_price = BASE_PRICES.get(location, 1500)
        total = base_price * duration
        
        await update.message.reply_text(
            f'Базова вартість: {total} грн\n\n'
            'Оберіть додаткові послуги (можна обрати декілька).\n'
            'Використовуйте кнопки:\n'
            '• ❌ Видалити послугу - для видалення послуги\n'
            '• 💰 Розрахувати вартість - для перегляду поточної вартості\n'
            '• ✅ Завершити вибір - для завершення замовлення',
            reply_markup=reply_markup
        )
        return CHOOSING_SERVICES
        
    except ValueError:
        await update.message.reply_text(
            "Невірний формат введення. Будь ласка, введіть тривалість у форматі:\n"
            "• Час у годинах (наприклад: 4)\n"
            "• Час у годинах з половиною (наприклад: 4.5)\n\n"
            "Доступні значення від 3.5 до 12 годин з кроком 0.5 години."
        )
        return ENTERING_CUSTOM_DURATION

async def service_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору додаткових послуг
    
    Returns:
        int: Стан CHOOSING_SERVICES або MAIN_MENU
    """
    choice = update.message.text
    
    if choice == '⬅️ Головне меню':
        context.user_data['state'] = MAIN_MENU
        return await show_main_menu(update, context)
    
    if choice == '❌ Видалити послугу':
        if not context.user_data.get('services'):
            await update.message.reply_text("У вас ще немає обраних послуг")
            return CHOOSING_SERVICES
        
        # Створення клавіатури з обраними послугами для видалення
        keyboard = [[KeyboardButton(service)] for service in context.user_data['services']]
        keyboard.append([KeyboardButton('↩️ Повернутись до вибору послуг')])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            'Оберіть послугу для видалення:',
            reply_markup=reply_markup
        )
        return CHOOSING_SERVICES
    
    if choice == '↩️ Повернутись до вибору послуг':
        context.user_data['state'] = CHOOSING_SERVICES
        # Створення клавіатури з додатковими послугами
        keyboard = []
        for service, info in ADDITIONAL_SERVICES.items():
            button_text = f"{service} ({info['price']} грн)"
            keyboard.append([KeyboardButton(button_text)])
        
        keyboard.append([KeyboardButton('❌ Видалити послугу')])
        keyboard.append([KeyboardButton('💰 Розрахувати вартість')])
        keyboard.append([KeyboardButton('✅ Завершити вибір')])
        keyboard.append([KeyboardButton('⬅️ Головне меню')])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            'Оберіть додаткові послуги (можна обрати декілька).\n'
            'Використовуйте кнопки:\n'
            '• ❌ Видалити послугу - для видалення послуги\n'
            '• 💰 Розрахувати вартість - для перегляду поточної вартості\n'
            '• ✅ Завершити вибір - для завершення замовлення',
            reply_markup=reply_markup
        )
        return CHOOSING_SERVICES
    
    if choice == '💰 Розрахувати вартість':
        location = context.user_data.get('location')
        duration = context.user_data.get('duration')
        services = context.user_data.get('services', [])
        city = context.user_data.get('city')
        district = context.user_data.get('district')
        
        price_info = format_price_info(location, duration, services, city, district)
        await update.message.reply_text(price_info)
        return CHOOSING_SERVICES
    
    if choice == '✅ Завершити вибір':
        # Переходимо до вибору району
        city = context.user_data.get('city')
        if city in TAXI_PRICES:
            keyboard = [[KeyboardButton(district)] for district in TAXI_PRICES[city].keys()]
            keyboard.append([KeyboardButton('⬅️ Головне меню')])
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                'Оберіть район, де буде проходити свято:',
                reply_markup=reply_markup
            )
            return CHOOSING_DISTRICT
        else:
            # Якщо місто не знайдено в TAXI_PRICES, пропускаємо вибір району
            return await confirm_order(update, context)
    
    # Обробка видалення послуги
    if choice in context.user_data.get('services', []):
        context.user_data['services'].remove(choice)
        await update.message.reply_text(f"Видалено: {choice}")
        
        # Створення клавіатури з додатковими послугами
        keyboard = []
        for service, info in ADDITIONAL_SERVICES.items():
            button_text = f"{service} ({info['price']} грн)"
            keyboard.append([KeyboardButton(button_text)])
        
        keyboard.append([KeyboardButton('❌ Видалити послугу')])
        keyboard.append([KeyboardButton('💰 Розрахувати вартість')])
        keyboard.append([KeyboardButton('✅ Завершити вибір')])
        keyboard.append([KeyboardButton('⬅️ Головне меню')])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            'Оберіть додаткові послуги (можна обрати декілька).\n'
            'Використовуйте кнопки:\n'
            '• ❌ Видалити послугу - для видалення послуги\n'
            '• 💰 Розрахувати вартість - для перегляду поточної вартості\n'
            '• ✅ Завершити вибір - для завершення замовлення',
            reply_markup=reply_markup
        )
        return CHOOSING_SERVICES
    
    # Обробка додавання нової послуги
    service_name = choice.split(' (')[0]  # Отримання назви послуги без ціни
    if service_name in ADDITIONAL_SERVICES and service_name not in context.user_data.get('services', []):
        if 'services' not in context.user_data:
            context.user_data['services'] = []
        context.user_data['services'].append(service_name)
        await update.message.reply_text(f"Додано: {service_name}")
    
    return CHOOSING_SERVICES

async def district_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка вибору району та підтвердження замовлення
    
    Returns:
        int: Стан MAIN_MENU
    """
    if update.message.text == '⬅️ Головне меню':
        context.user_data['state'] = MAIN_MENU
        return await show_main_menu(update, context)
    
    district = update.message.text
    context.user_data['district'] = district
    
    # Розраховуємо вартість з урахуванням району
    location = context.user_data.get('location')
    duration = context.user_data.get('duration')
    services = context.user_data.get('services', [])
    city = context.user_data.get('city')
    
    service_price, taxi_price = calculate_total_price(location, duration, services, city, district)
    total_price = service_price + taxi_price
    
    # Форматуємо інформацію про замовлення
    order_info = (
        f"🎉 Нове замовлення:\n\n"
        f"🏙 Місто: {city}\n"
        f"🏘 Район: {district}\n"
        f"🎈 Тип події: {context.user_data.get('event_type')}\n"
        f"📍 Локація: {location}\n"
        f"⏱ Тривалість: {duration}\n"
        f"💰 Вартість послуг: {service_price} грн\n"
        f"🚕 Вартість таксі: {taxi_price} грн\n"
        f"💵 Загальна вартість: {total_price} грн\n"
    )
    
    if services:
        order_info += "\nДодаткові послуги:\n"
        for service in services:
            order_info += f"• {service}\n"
    
    # Створюємо кнопки підтвердження
    keyboard = [
        [InlineKeyboardButton("✅ Підтвердити замовлення", callback_data="confirm_order")],
        [InlineKeyboardButton("❌ Скасувати", callback_data="cancel_order")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"{order_info}\n\n"
        "Будь ласка, підтвердіть ваше замовлення:",
        reply_markup=reply_markup
    )
    
    return CONFIRM_ORDER

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Скасування розмови
    
    Returns:
        int: ConversationHandler.END
    """
    await update.message.reply_text('Розмову скасовано. Щоб почати спочатку, використайте команду /start')
    return ConversationHandler.END

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка команди для надсилання повідомлення від менеджера
    
    Підтримує:
    - Надсилання повідомлень конкретним користувачам
    - Розсилку всім користувачам
    - Надсилання файлів з повідомленнями
    """
    if str(update.effective_user.id) != str(MANAGER_CHAT_ID):
        await update.message.reply_text("Ця команда доступна тільки для менеджера")
        return
    
    if not context.args:
        await update.message.reply_text(
            "Використання:\n"
            "/send <user_id> <повідомлення> - надіслати повідомлення конкретному користувачу\n"
            "/broadcast <повідомлення> - розіслати повідомлення всім користувачам\n\n"
            "Для надсилання файлу:\n"
            "1. Надішліть файл боту\n"
            "2. Відповідь на файл командою /send <user_id> <повідомлення> або /broadcast <повідомлення>"
        )
        return
    
    # Перевірка наявності файлу у відповіді
    if update.message.reply_to_message and (
        update.message.reply_to_message.document or 
        update.message.reply_to_message.photo or 
        update.message.reply_to_message.video or 
        update.message.reply_to_message.audio
    ):
        file_message = update.message.reply_to_message
        command = context.args[0]
        
        if command == 'broadcast':
            message = ' '.join(context.args[1:])
            users = user_data.get_all_users()
            success = 0
            failed = 0
            blocked = 0
            
            # Розсилка файлу всім користувачам
            for user_id in users:
                try:
                    if file_message.document:
                        await context.bot.send_document(
                            chat_id=user_id,
                            document=file_message.document.file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    elif file_message.photo:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=file_message.photo[-1].file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    elif file_message.video:
                        await context.bot.send_video(
                            chat_id=user_id,
                            video=file_message.video.file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    elif file_message.audio:
                        await context.bot.send_audio(
                            chat_id=user_id,
                            audio=file_message.audio.file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    success += 1
                except telegram.error.Forbidden:
                    blocked += 1
                    logger.warning(f"Користувач {user_id} заблокував бота")
                except Exception as e:
                    logger.error(f"Помилка при відправці файлу користувачу {user_id}: {str(e)}")
                    failed += 1
            
            await update.message.reply_text(
                f"Розсилка файлу завершена:\n"
                f"✅ Успішно: {success}\n"
                f"❌ Помилок: {failed}\n"
                f"🚫 Заблоковано: {blocked}"
            )
        else:
            try:
                target_user_id = int(command)
                message = ' '.join(context.args[1:])
                
                user_info = user_data.get_user(target_user_id)
                if not user_info:
                    await update.message.reply_text(f"Користувач з ID {target_user_id} не знайдений")
                    return
                
                # Надсилання файлу конкретному користувачу
                try:
                    if file_message.document:
                        await context.bot.send_document(
                            chat_id=target_user_id,
                            document=file_message.document.file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    elif file_message.photo:
                        await context.bot.send_photo(
                            chat_id=target_user_id,
                            photo=file_message.photo[-1].file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    elif file_message.video:
                        await context.bot.send_video(
                            chat_id=target_user_id,
                            video=file_message.video.file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    elif file_message.audio:
                        await context.bot.send_audio(
                            chat_id=target_user_id,
                            audio=file_message.audio.file_id,
                            caption=f"📢 Повідомлення від менеджера:\n\n{message}"
                        )
                    
                    await update.message.reply_text(
                        f"Файл надіслано користувачу:\n"
                        f"ID: {target_user_id}\n"
                        f"Ім'я: {user_info.get('first_name', 'Невідомо')}\n"
                        f"Username: @{user_info.get('username', 'Невідомо')}"
                    )
                except telegram.error.Forbidden:
                    await update.message.reply_text(f"Користувач {target_user_id} заблокував бота")
            except ValueError:
                await update.message.reply_text("Невірний формат ID користувача")
    else:
        # Обробка текстового повідомлення
        command = context.args[0]
        if command == 'broadcast':
            message = ' '.join(context.args[1:])
            if not message:
                await update.message.reply_text("Будь ласка, вкажіть текст повідомлення")
                return
            
            users = user_data.get_all_users()
            if not users:
                await update.message.reply_text("Поки що немає користувачів для розсилки")
                return
                
            success = 0
            failed = 0
            blocked = 0
            
            # Розсилка текстового повідомлення всім користувачам
            for user_id in users:
                try:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"📢 Повідомлення від менеджера:\n\n{message}"
                    )
                    success += 1
                except telegram.error.Forbidden:
                    blocked += 1
                    logger.warning(f"Користувач {user_id} заблокував бота")
                except Exception as e:
                    logger.error(f"Помилка при відправці повідомлення користувачу {user_id}: {str(e)}")
                    failed += 1
            
            await update.message.reply_text(
                f"Розсилка завершена:\n"
                f"✅ Успішно: {success}\n"
                f"❌ Помилок: {failed}\n"
                f"🚫 Заблоковано: {blocked}"
            )
        else:
            try:
                target_user_id = int(command)
                message = ' '.join(context.args[1:])
                
                if not message:
                    await update.message.reply_text("Будь ласка, вкажіть текст повідомлення")
                    return
                
                user_info = user_data.get_user(target_user_id)
                if not user_info:
                    await update.message.reply_text(f"Користувач з ID {target_user_id} не знайдений")
                    return
                
                # Надсилання текстового повідомлення конкретному користувачу
                try:
                    await context.bot.send_message(
                        chat_id=target_user_id,
                        text=f"📢 Повідомлення від менеджера:\n\n{message}"
                    )
                    
                    await update.message.reply_text(
                        f"Повідомлення надіслано користувачу:\n"
                        f"ID: {target_user_id}\n"
                        f"Ім'я: {user_info.get('first_name', 'Невідомо')}\n"
                        f"Username: @{user_info.get('username', 'Невідомо')}"
                    )
                except telegram.error.Forbidden:
                    await update.message.reply_text(f"Користувач {target_user_id} заблокував бота")
            except ValueError:
                await update.message.reply_text("Невірний формат ID користувача")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробка команди /broadcast для розсилки повідомлень та файлів всім користувачам
    
    Args:
        update: Оновлення від Telegram
        context: Контекст бота
    """
    if str(update.effective_user.id) != str(MANAGER_CHAT_ID):
        await update.message.reply_text("Ця команда доступна тільки для менеджера")
        return
    
    # Перевірка наявності файлу у відповіді
    if update.message.reply_to_message and (
        update.message.reply_to_message.document or 
        update.message.reply_to_message.photo or 
        update.message.reply_to_message.video or 
        update.message.reply_to_message.audio
    ):
        file_message = update.message.reply_to_message
        message = ' '.join(context.args) if context.args else ""
        
        users = user_data.get_all_users()
        if not users:
            await update.message.reply_text("Поки що немає користувачів для розсилки")
            return
            
        success = 0
        failed = 0
        
        # Розсилка файлу всім користувачам
        for user_id in users:
            try:
                if file_message.document:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=file_message.document.file_id,
                        caption=f"📢 Повідомлення від менеджера:\n\n{message}" if message else None
                    )
                elif file_message.photo:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=file_message.photo[-1].file_id,
                        caption=f"📢 Повідомлення від менеджера:\n\n{message}" if message else None
                    )
                elif file_message.video:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=file_message.video.file_id,
                        caption=f"📢 Повідомлення від менеджера:\n\n{message}" if message else None
                    )
                elif file_message.audio:
                    await context.bot.send_audio(
                        chat_id=user_id,
                        audio=file_message.audio.file_id,
                        caption=f"📢 Повідомлення від менеджера:\n\n{message}" if message else None
                    )
                success += 1
            except Exception as e:
                logger.error(f"Помилка при відправці файлу користувачу {user_id}: {str(e)}")
                failed += 1
        
        await update.message.reply_text(
            f"Розсилка файлу завершена:\n"
            f"✅ Успішно: {success}\n"
            f"❌ Помилок: {failed}"
        )
        return
    
    # Обробка текстового повідомлення
    if not context.args:
        await update.message.reply_text(
            "Використання:\n"
            "/broadcast <повідомлення> - розіслати повідомлення всім користувачам\n\n"
            "Для надсилання файлу:\n"
            "1. Надішліть файл боту\n"
            "2. Відповідь на файл командою /broadcast <повідомлення>"
        )
        return
    
    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Будь ласка, вкажіть текст повідомлення")
        return
    
    users = user_data.get_all_users()
    if not users:
        await update.message.reply_text("Поки що немає користувачів для розсилки")
        return
        
    success = 0
    failed = 0
    
    # Розсилка повідомлення всім користувачам
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 Повідомлення від менеджера:\n\n{message}"
            )
            success += 1
        except Exception as e:
            logger.error(f"Помилка при відправці повідомлення користувачу {user_id}: {str(e)}")
            failed += 1
    
    await update.message.reply_text(
        f"Розсилка завершена:\n"
        f"✅ Успішно: {success}\n"
        f"❌ Помилок: {failed}"
    )

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Відправляє список всіх користувачів у форматі Excel файлу"""
    if str(update.effective_user.id) != str(MANAGER_CHAT_ID):
        await update.message.reply_text("Ця команда доступна тільки для менеджера")
        return

    # Отримуємо дані користувачів
    users_data = user_data.get_all_users()
    
    if not users_data:
        await update.message.reply_text("Поки що немає зареєстрованих користувачів.")
        return

    # Створюємо DataFrame
    users_list = []
    for user_id, user_info in users_data.items():
        user_dict = {
            'ID': user_id,
            "Ім'я": user_info.get('first_name', ''),
            'Прізвище': user_info.get('last_name', ''),
            'Username': user_info.get('username', ''),
            'Мова': user_info.get('language_code', ''),
            'Дата реєстрації': user_info.get('registration_date', ''),
            'Останній візит': user_info.get('last_visit', ''),
            'Кількість замовлень': len(user_info.get('orders', [])),
            'Статус': user_info.get('status', 'Активний')
        }
        users_list.append(user_dict)

    df = pd.DataFrame(users_list)
    
    # Створюємо файл Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"users_list_{timestamp}.xlsx"
    
    # Налаштовуємо стилі
    writer = pd.ExcelWriter(filename, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Користувачі')
    
    # Отримуємо об'єкт worksheet
    worksheet = writer.sheets['Користувачі']
    
    # Налаштовуємо ширину стовпців
    for column in worksheet.columns:
        max_length = 0
        column = [cell for cell in column]
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
    
    # Зберігаємо файл
    writer.close()
    
    # Відправляємо файл
    try:
        with open(filename, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=filename,
                caption=f"Список користувачів станом на {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            )
        # Видаляємо тимчасовий файл
        os.remove(filename)
    except Exception as e:
        await update.message.reply_text(f"Помилка при відправці файлу: {str(e)}")
        if os.path.exists(filename):
            os.remove(filename)

async def confirm_order(update: Update, context: CallbackContext) -> int:
    """Підтвердження замовлення"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    user = user_data[user_id]
    
    # Отримуємо всі дані замовлення
    city = context.user_data.get('city')
    district = user.get('district')
    location = user.get('location')
    duration = user.get('duration')
    services = user.get('services', [])
    
    # Розраховуємо вартість
    service_price, taxi_price = calculate_total_price(location, duration, services, city, district)
    total_price = service_price + taxi_price
    
    # Форматуємо інформацію про замовлення
    order_info = (
        f"✅ Замовлення підтверджено!\n\n"
        f"📍 Місто: {city}\n"
        f"🏘 Район: {district}\n"
        f"🏢 Локація: {location}\n"
        f"⏱ Тривалість: {duration}\n"
        f"💰 Вартість послуг: {service_price} грн\n"
        f"🚕 Вартість таксі: {taxi_price} грн\n"
        f"💵 Загальна вартість: {total_price} грн\n"
    )
    
    if services:
        order_info += "\nДодаткові послуги:\n"
        for service in services:
            order_info += f"• {service}\n"
    
    # Відправляємо інформацію про замовлення менеджеру
    manager_message = (
        f"🆕 Нове замовлення!\n\n"
        f"👤 Користувач: {update.effective_user.full_name}\n"
        f"📱 ID: {user_id}\n\n"
        f"{order_info}"
    )
    
    await context.bot.send_message(
        chat_id=MANAGER_CHAT_ID,
        text=manager_message
    )
    
    # Відправляємо підтвердження користувачу
    await query.edit_message_text(
        text=f"{order_info}\n\n"
             f"📞 Наш менеджер зв'яжеться з вами найближчим часом для уточнення деталей.\n"
             f"Дякуємо за замовлення! 🎉"
    )
    
    # Очищаємо дані замовлення
    user_data[user_id] = {}
    
    return ConversationHandler.END

def main():
    """
    Головна функція для запуску бота
    
    Налаштовує обробники команд та запускає бота
    """
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Налаштування обробника розмови
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)],
            CONTACT_MANAGER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manager_contact)],
            WRITING_FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
            WRITING_COMPLAINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
            WRITING_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
            VIEWING_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_service_details)],
            CHOOSING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_chosen)],
            CHOOSING_EVENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_type_chosen)],
            CHOOSING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_chosen)],
            CHOOSING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, duration_chosen)],
            CHOOSING_SERVICES: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_chosen)],
            ENTERING_CUSTOM_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_duration)],
            CHOOSING_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district_chosen)],
            CONFIRM_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Додавання обробників команд для менеджера
    application.add_handler(CommandHandler('send', send_message))
    application.add_handler(CommandHandler('broadcast', broadcast_message))
    application.add_handler(CommandHandler('users', users_command))
    
    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main() 
