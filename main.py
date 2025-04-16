import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import (
    TELEGRAM_BOT_TOKEN, MANAGER_CHAT_ID, CITIES, EVENT_TYPES, LOCATIONS, 
    DURATIONS, ADDITIONAL_SERVICES, BASE_PRICES, DURATION_MULTIPLIERS
)
from user_data import user_data
from datetime import datetime
import pandas as pd

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
 CHOOSING_DURATION, CHOOSING_SERVICES) = range(4, 9)

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

def calculate_total_price(location, duration, services):
    """
    Розрахунок загальної вартості замовлення
    
    Args:
        location (str): Обрана локація
        duration (str): Обрана тривалість
        services (list): Список обраних додаткових послуг
        
    Returns:
        int: Загальна вартість замовлення
    """
    # Базова ціна за локацію
    base_price = BASE_PRICES.get(location, 1500)
    
    # Множник за тривалість
    duration_multiplier = DURATION_MULTIPLIERS.get(duration, 1)
    
    # Розрахунок базової вартості
    total = base_price * duration_multiplier
    
    # Додавання вартості додаткових послуг
    for service in services:
        service_info = ADDITIONAL_SERVICES.get(service)
        if service_info:
            total += service_info['price']
    
    return total

def format_price_info(location, duration, services):
    """
    Форматування інформації про ціни для відображення користувачу
    
    Args:
        location (str): Обрана локація
        duration (str): Обрана тривалість
        services (list): Список обраних додаткових послуг
        
    Returns:
        str: Відформатований текст з інформацією про ціни
    """
    base_price = BASE_PRICES.get(location, 1500)
    duration_multiplier = DURATION_MULTIPLIERS.get(duration, 1)
    base_total = base_price * duration_multiplier
    
    info = (
        f"💰 Розрахунок вартості:\n\n"
        f"Базова вартість ({location}): {base_price} грн\n"
        f"Тривалість ({duration}): x{duration_multiplier}\n"
        f"Базова вартість з урахуванням часу: {base_total} грн\n\n"
    )
    
    if services:
        info += "Додаткові послуги:\n"
        services_total = 0
        for service in services:
            service_info = ADDITIONAL_SERVICES.get(service)
            if service_info:
                price = service_info['price']
                services_total += price
                info += f"• {service}: {price} грн\n"
        info += f"\nВартість додаткових послуг: {services_total} грн\n"
        info += f"Загальна вартість: {base_total + services_total} грн"
    else:
        info += f"Загальна вартість: {base_total} грн"
    
    return info

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
        int: Стан MAIN_MENU
    """
    user = update.effective_user
    
    # Формування повідомлення для менеджера
    manager_message = (
        f"💬 Запит на зв'язок від користувача:\n\n"
        f"👤 Інформація про користувача:\n"
        f"ID: {user.id}\n"
        f"Ім'я: {user.first_name}"
    )
    if user.last_name:
        manager_message += f" {user.last_name}"
    if user.username:
        manager_message += f"\nUsername: @{user.username}"
    
    # Відправка повідомлення менеджеру
    await context.bot.send_message(
        chat_id=MANAGER_CHAT_ID,
        text=manager_message
    )
    
    # Відправка підтвердження користувачу
    await update.message.reply_text(
        "Дякуємо за звернення! Наш менеджер зв'яжеться з вами найближчим часом.\n"
        "А поки ви можете ознайомитись з нашими послугами або оформити замовлення."
    )
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
    for service in SERVICE_DETAILS.keys():
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
    
    if service_name in SERVICE_DETAILS:
        service = SERVICE_DETAILS[service_name]
        
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
    
    user_data.add_user(user.id, user_info)
    
    # Формування повідомлення про нового користувача
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
    
    # Очищення даних попереднього замовлення
    context.user_data.clear()
    # Збереження інформації про користувача
    context.user_data['user'] = user
    # Встановлення початкового стану
    context.user_data['state'] = MAIN_MENU
    
    # Відправка привітання користувачу
    await update.message.reply_text(
        f"Вітаю, {user.first_name}! 🎉\n"
        "Я допоможу вам організувати незабутнє свято!"
    )
    return await show_main_menu(update, context)

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
    
    # Вибір доступних тривалостей залежно від локації
    if 'Домой' in location or 'кафе' in location:
        durations = DURATIONS['Домой/кафе']
    elif 'Турбаза' in location:
        durations = DURATIONS['Турбаза']
    elif 'Садик-школа' in location:
        durations = DURATIONS['Садик-школа']
    else:
        durations = DURATIONS['Домой/кафе']
    
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
        
        price_info = format_price_info(location, duration, services)
        await update.message.reply_text(price_info)
        return CHOOSING_SERVICES
    
    if choice == '✅ Завершити вибір':
        context.user_data['state'] = MAIN_MENU
        location = context.user_data.get('location')
        duration = context.user_data.get('duration')
        services = context.user_data.get('services', [])
        
        # Формування підсумкового повідомлення про замовлення
        summary = (
            f"🎉 Нове замовлення:\n\n"
            f"🏙 Місто: {context.user_data.get('city')}\n"
            f"🎈 Тип події: {context.user_data.get('event_type')}\n"
            f"📍 Локація: {location}\n"
            f"⏱ Тривалість: {duration}\n"
            f"🎁 Додаткові послуги:\n"
        )
        
        if services:
            for service in services:
                summary += f"   • {service}\n"
        else:
            summary += "   • Не обрано\n"
        
        # Додавання інформації про вартість
        price_info = format_price_info(location, duration, services)
        summary += f"\n{price_info}"
        
        # Відправка повідомлення менеджеру
        await send_to_manager(context, context.user_data, summary)
        
        # Відправка підтвердження клієнту
        await update.message.reply_text(
            summary + "\nДякуємо за замовлення! Наш менеджер зв'яжеться з вами найближчим часом."
        )
        return await show_main_menu(update, context)
    
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
                except Exception as e:
                    logger.error(f"Помилка при відправці файлу користувачу {user_id}: {str(e)}")
                    failed += 1
            
            await update.message.reply_text(
                f"Розсилка файлу завершена:\n"
                f"✅ Успішно: {success}\n"
                f"❌ Помилок: {failed}"
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
            
            # Розсилка текстового повідомлення всім користувачам
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
            VIEWING_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_service_details)],
            CHOOSING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_chosen)],
            CHOOSING_EVENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_type_chosen)],
            CHOOSING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_chosen)],
            CHOOSING_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, duration_chosen)],
            CHOOSING_SERVICES: [MessageHandler(filters.TEXT & ~filters.COMMAND, service_chosen)],
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
