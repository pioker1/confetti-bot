# ============================================
# ІМПОРТИ ТА НАЛАШТУВАННЯ
# ============================================
import logging
import os
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from config import (
    TELEGRAM_BOT_TOKEN, CITIES, EVENT_TYPES_LIST,
    CITY_CHANNELS, GENERAL_INFO, MANAGER_INFO, MANAGER_CONTACT_MESSAGES, MANAGER_CHAT_ID,
    LOCATION_PDF_FILES, LOCATIONS, LOCATION_INFO, THEMES, THEME_INFO, THEME_BTN, Hello_World, THEME_PHOTOS, EVENT_FORMATS, HOURLY_PRICES, PAKET_PRICES, PAKET_PHOTOS, QWEST, QWEST_PHOTOS, ADDITIONAL_SERVICES_WITH_SUBMENU, ADDITIONAL_SERVICES_SINGLE, ADDITIONAL_SERVICES_PHOTOS, TAXI_PRICES, FAMILY_INFO, FAMILY_INFO_INFO2, FAMALY_TRIP
)
from user_data import user_data
from datetime import datetime
import telegram.ext._updater as _updater_module
import pandas as pd
from io import BytesIO

# --- ФУНКЦІЯ УНІФІКАЦІЇ КОРИСТУВАЧА ---
def get_unified_user_info(user, old_user=None, update=None, chat=None, phone=None):
    now = datetime.now().isoformat()
    return {
        'user_id': getattr(user, 'id', None),
        'username': getattr(user, 'username', None),
        'first_name': getattr(user, 'first_name', None),
        'last_name': getattr(user, 'last_name', None),
        'language_code': getattr(user, 'language_code', None),
        'is_bot': getattr(user, 'is_bot', None),
        'status': (old_user or {}).get('status', None),
        'last_update': now,
        'created_at': (old_user or {}).get('created_at', now),
        'phone_number': phone or (old_user or {}).get('phone_number', None),
        'chat_id': getattr(chat, 'id', None) if chat else (old_user or {}).get('chat_id', None),
        'type': getattr(chat, 'type', None) if chat else (old_user or {}).get('type', None),
        'full_user_obj': user.to_dict() if hasattr(user, 'to_dict') else str(user),
        'device_info': (old_user or {}).get('device_info', None),
        'visits': (old_user or {}).get('visits', 0),
        'order_count': (old_user or {}).get('order_count', 0),
    }

# Додаємо slot для `_Updater__polling_cleanup_cb` щоб уникнути AttributeError при build()
_updater_module.Updater.__slots__ = (*_updater_module.Updater.__slots__, '_Updater__polling_cleanup_cb')

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# КОНСТАНТИ ТА СТАНИ
# ============================================
# Стани розмови
CHOOSING_CITY, CHOOSING_EVENT_TYPE, CHOOSING_EVENT_TYPE_Sim_svjata, CHOOSING_EVENT_TYPE_inshe, CHOOSING_EVENT_TYPE_afisha, CHOOSING_LOCATION, CHOOSING_LOCATION_inshe, CHOOSING_THEME, CHOOSING_THEME2, CHOOSING_THEME_DETAILS, CHOOSING_FORMAT, CHOOSING_HOURLY_PRICE, CHOOSING_PACKAGE, CHOOSING_QWEST, CHOOSING_QWEST_DURATION, CHOOSING_FINAL, CHOOSING_ADDITIONAL_SERVICES, CHOOSING_SERVICE_OPTION, CHOOSING_DISTRICT, CHOOSING_SUMMARY,PHONE_CONTACT, FFMILY_DOP = range(22)

STATE_NAMES = {
    CHOOSING_CITY: 'CHOOSING_CITY',
    CHOOSING_EVENT_TYPE: 'CHOOSING_EVENT_TYPE',
    CHOOSING_EVENT_TYPE_Sim_svjata: 'CHOOSING_EVENT_TYPE_Sim_svjata',
    FFMILY_DOP: 'FFMILY_DOP',
    CHOOSING_EVENT_TYPE_inshe: 'CHOOSING_EVENT_TYPE_inshe',
    CHOOSING_EVENT_TYPE_afisha: 'CHOOSING_EVENT_TYPE_afisha',
    CHOOSING_LOCATION: 'CHOOSING_LOCATION',
    CHOOSING_LOCATION_inshe: 'CHOOSING_LOCATION_inshe',
    CHOOSING_THEME: 'CHOOSING_THEME',
    CHOOSING_THEME2: 'CHOOSING_THEME2',
    CHOOSING_THEME_DETAILS: 'CHOOSING_THEME_DETAILS',
    CHOOSING_FORMAT: 'CHOOSING_FORMAT',
    CHOOSING_HOURLY_PRICE: 'CHOOSING_HOURLY_PRICE',
    CHOOSING_PACKAGE: 'CHOOSING_PACKAGE',
    CHOOSING_QWEST: 'CHOOSING_QWEST',
    CHOOSING_QWEST_DURATION: 'CHOOSING_QWEST_DURATION',
    CHOOSING_FINAL: 'CHOOSING_FINAL',
    CHOOSING_ADDITIONAL_SERVICES: 'CHOOSING_ADDITIONAL_SERVICES',
    CHOOSING_SERVICE_OPTION: 'CHOOSING_SERVICE_OPTION',
    CHOOSING_DISTRICT: 'CHOOSING_DISTRICT',
    CHOOSING_SUMMARY: 'CHOOSING_SUMMARY',
    PHONE_CONTACT: 'PHONE_CONTACT'
}

# Кнопки
BACK_BUTTON = "⬅️ Назад"
CONTACT_MANAGER_BUTTON = "📞 Зв'язатися з менеджером"
SUGGEST_LOCATION_BUTTON = "🗺 Підказати вибір місця проведення"
WOW_BUTTON = "Вау! 😍"
NEXT_BUTTON = "➡️ Далі"
DELETE_CHOICE_BUTTON = "🗑 Видалити вибір"
ADDITIONAL_SERVICES_BUTTON = "➕ Додаткові послуги"

# Додаємо нову константу для кнопки показу вибраних послуг
SHOW_SELECTED_SERVICES_BUTTON = "📋 Показати вибрані послуги"

# ============================================
# ФУНКЦІЇ ДЛЯ РОБОТИ З ВИБОРАМИ КОРИСТУВАЧА
# ============================================
def vibir(context: ContextTypes.DEFAULT_TYPE) -> str:
    """Повертає рядок з усіма виборами користувача"""
    if not context.user_data.get('choices'):
        return "Користувач ще не зробив жодного вибору"
    
    result = "Вибори користувача:\n"
    for choice in context.user_data['choices']:
        result += f"- {choice['type']}: {choice['value']}\n"
    return result

def remove_choice_by_type(context: ContextTypes.DEFAULT_TYPE, choice_type: str) -> None:
    """Видаляє всі вибори користувача за типом"""
    try:
        initialize_user_choices(context)
        if not context.user_data.get('choices'):
            logger.warning(f"Спроба видалити вибори типу {choice_type}, але список виборів порожній")
            return

        original_length = len(context.user_data['choices'])
        context.user_data['choices'] = [
            choice for choice in context.user_data['choices']
            if choice['type'] != choice_type
        ]
        removed_count = original_length - len(context.user_data['choices'])
        logger.info(f"Видалено {removed_count} виборів типу: {choice_type}")
    except Exception as e:
        logger.error(f"Помилка при видаленні виборів типу {choice_type}: {str(e)}")
        raise

def initialize_user_choices(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ініціалізує структуру для збереження виборів користувача"""
    try:
        if 'choices' not in context.user_data:
            context.user_data['choices'] = []
            logger.info("Ініціалізовано новий список виборів користувача")
    except Exception as e:
        logger.error(f"Помилка при ініціалізації виборів користувача: {str(e)}")
        raise

def add_choice(context: ContextTypes.DEFAULT_TYPE, choice_type: str, value: str) -> None:
    """Додає вибір користувача до історії, видаляючи попередній такого ж типу для 'Формат', 'Погодинна ціна', 'Пакет'."""
    try:
        initialize_user_choices(context)
        if not isinstance(choice_type, str) or not isinstance(value, str):
            logger.error(f"Невірний тип даних для вибору: type={type(choice_type)}, value={type(value)}")
            raise ValueError("Тип та значення вибору повинні бути рядками")
        # Видаляємо попередній вибір того ж типу для унікальних категорій
        if choice_type in ["Формат", "Погодинна ціна", "Пакет"]:
            remove_choice_by_type(context, choice_type)
        context.user_data['choices'].append({'type': choice_type, 'value': value})
        logger.info(f"Додано вибір: {choice_type} = {value}")
    except Exception as e:
        logger.error(f"Помилка при додаванні вибору: {str(e)}")
        raise

# ============================================
# ФУНКЦІЇ ДЛЯ СТВОРЕННЯ КЛАВІАТУР
# ============================================
def create_city_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру з доступними містами"""
    keyboard = [[KeyboardButton(city)] for city in CITIES]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def create_event_type_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру з типами подій"""
    keyboard = []
    for i in range(0, len(EVENT_TYPES_LIST), 2):
        row = [KeyboardButton(EVENT_TYPES_LIST[i])]
        if i + 1 < len(EVENT_TYPES_LIST):
            row.append(KeyboardButton(EVENT_TYPES_LIST[i + 1]))
        keyboard.append(row)
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_theme_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру з тематиками свят"""
    keyboard = []
    for i in range(0, len(THEMES), 2):
        row = [KeyboardButton(THEMES[i])]
        if i + 1 < len(THEMES):
            row.append(KeyboardButton(THEMES[i + 1]))
        keyboard.append(row)
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_theme2_keyboard(theme: str, city: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру з підтемами для вибраної тематики та міста"""
    try:
        # Отримуємо список підтем для вибраної тематики та міста
        from config import THEME_BTN
        subthemes = THEME_BTN.get(city, {}).get(theme, [])
        if not subthemes:
            logger.warning(f"Не знайдено підтем для тематики: {theme} у місті: {city}")
            return create_theme_keyboard()

        # Створюємо клавіатуру
        keyboard = []
        for i in range(0, len(subthemes), 2):
            row = [KeyboardButton(subthemes[i])]
            if i + 1 < len(subthemes):
                row.append(KeyboardButton(subthemes[i + 1]))
            keyboard.append(row)
            
        # Додаємо кнопку "Назад"
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури підтем: {str(e)}")
        return create_theme_keyboard()

def create_other_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру для першого рівня розділу 'Інше'"""
    keyboard = [
        [KeyboardButton(CONTACT_MANAGER_BUTTON)],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_sim_svjata_keyboard_with_back(famaly_trip, city=None):
    """Створює клавіатуру для сімейних свят з кнопкою назад та цінами"""
    keyboard = []
    # Якщо місто задано, беремо лише його сервіси, інакше всі сервіси першого міста
    if city and city in famaly_trip:
        services = famaly_trip[city]
    else:
        # Якщо місто не задано, показуємо сервіси першого міста (наприклад, Київ)
        services = next(iter(famaly_trip.values()))
    for service, price in services.items():
        button_text = f"{service} - {price} грн"
        keyboard.append([KeyboardButton(button_text)])
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_location_keyboard(event_type: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру з доступними локаціями для конкретного типу події"""
    try:
        # Отримуємо список локацій для даного типу події
        locations = LOCATIONS.get(event_type, [])
        if not locations:
            logger.warning(f"Не знайдено локацій для типу події: {event_type}")
            locations = ['📍 Інше']  # Запасний варіант

        # Створюємо клавіатуру
        keyboard = []
        for i in range(0, len(locations), 2):
            row = [KeyboardButton(locations[i])]
            if i + 1 < len(locations):
                row.append(KeyboardButton(locations[i + 1]))
            keyboard.append(row)
        
        
        # Додаємо кнопку "Назад"
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури локацій: {str(e)}")
        # Повертаємо просту клавіатуру з кнопкою "Назад" у випадку помилки
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)
    
    

def create_theme_details_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру для деталей теми"""
    try:
        keyboard = [
            [KeyboardButton("💰 Ціни")],
            [KeyboardButton(BACK_BUTTON)]
        ]
        logger.info("Створено клавіатуру theme_details_keyboard")
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури theme_details_keyboard: {str(e)}")
        raise

def create_format_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру для вибору формату свята"""
    try:
        # Створюємо клавіатуру з форматами
        keyboard = []
        for format_name in EVENT_FORMATS.keys():
            keyboard.append([KeyboardButton(format_name)])
        
        # Додаємо кнопку "Назад"
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури форматів: {str(e)}")
        # Повертаємо просту клавіатуру з кнопкою "Назад" у випадку помилки
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)
            

def create_hourly_price_keyboard(city: str, event_type: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру для вибору погодинної ціни"""
    try:
        keyboard = []
        
        # Отримуємо ціни для вибраного міста та типу події
        prices = HOURLY_PRICES[city][event_type]
        
        # Додаємо кнопки з цінами
        for price_name, price_value in prices.items():
            keyboard.append([KeyboardButton(f"{price_name}: {price_value} грн")])
        
        # Додаємо кнопку для зв'язку з менеджером
        keyboard.append([KeyboardButton(CONTACT_MANAGER_BUTTON)])
        
        # Додаємо кнопку "Назад"
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури погодинних цін: {str(e)}")
        # Повертаємо просту клавіатуру з кнопкою "Назад" у випадку помилки
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)

def create_package_keyboard(city: str, event_type: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру для вибору пакету"""
    try:
        keyboard = []
        packages = PAKET_PRICES[city][event_type].keys()
        
        for package in packages:
            keyboard.append([KeyboardButton(package)])
            
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури пакетів: {str(e)}")
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)

def create_qwest_keyboard(city: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру з квестами для вибраного міста"""
    try:
        keyboard = []
        qwests = QWEST.get(city, {})
        
        for qwest_name in qwests.keys():
            keyboard.append([KeyboardButton(qwest_name)])
            
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури квестів: {str(e)}")
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)

def create_qwest_duration_keyboard(qwest_name: str, city: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру для вибору тривалості квесту"""
    try:
        keyboard = []
        durations = QWEST[city][qwest_name].keys()
        
        for duration in durations:
            price = QWEST[city][qwest_name][duration]
            keyboard.append([KeyboardButton(f"{duration} - {price} грн")])
            
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури тривалості квесту: {str(e)}")
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)

def create_final_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру для фінального вибору"""
    keyboard = [
        [KeyboardButton(WOW_BUTTON)],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_selected_services_keyboard(context: ContextTypes.DEFAULT_TYPE, city: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру з вибраними послугами для видалення"""
    keyboard = []
    
    # Додаємо всі вибрані послуги як кнопки
    if 'additional_services' in context.user_data:
        for service, option in context.user_data['additional_services'].items():
            # Форматуємо текст кнопки
            button_text = f"❌ {service}: {option}"
            keyboard.append([KeyboardButton(button_text)])
    
    # Додаємо кнопки навігації
    keyboard.append([KeyboardButton(BACK_BUTTON)])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_additional_services_keyboard(city: str, context: ContextTypes.DEFAULT_TYPE = None) -> ReplyKeyboardMarkup:
    """Створює клавіатуру для вибору додаткових послуг"""
    try:
        keyboard = []
        
        # Додаємо послуги з підменю
        if city in ADDITIONAL_SERVICES_WITH_SUBMENU:
            services = ADDITIONAL_SERVICES_WITH_SUBMENU[city].keys()
            for service in services:
                keyboard.append([KeyboardButton(service)])
            
        # Додаємо прості послуги
        if city in ADDITIONAL_SERVICES_SINGLE:
            simple_services = ADDITIONAL_SERVICES_SINGLE[city].items()
            for service, price in simple_services:
                # Форматуємо ціну в залежності від типу
                if isinstance(price, str):
                    price_text = price
                else:
                    price_text = f"{price} грн"
                keyboard.append([KeyboardButton(f"{service} - {price_text}")])
        
        # Додаємо кнопки керування
        if context and context.user_data.get('additional_services'):
            keyboard.append([KeyboardButton(SHOW_SELECTED_SERVICES_BUTTON)])
        keyboard.append([KeyboardButton(NEXT_BUTTON)])
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури додаткових послуг: {str(e)}")
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)

def create_service_options_keyboard(city: str, service: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру для вибору опцій послуги"""
    try:
        keyboard = []
        options = ADDITIONAL_SERVICES_WITH_SUBMENU[city][service]
        
        for option, price in options.items():
            if isinstance(price, str):
                price_text = price
            else:
                price_text = f"{price} грн"
            keyboard.append([KeyboardButton(f"{option} - {price_text}")])
            
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури опцій послуги: {str(e)}")
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)

def create_district_keyboard(city: str) -> ReplyKeyboardMarkup:
    """Створює клавіатуру з районами міста"""
    try:
        keyboard = []
        districts = TAXI_PRICES[city].keys()
        
        # Створюємо кнопки для кожного району (по 2 в рядку)
        current_row = []
        for district in districts:
            if district != 'Інше':  # Додаємо всі райони, крім 'Інше'
                current_row.append(KeyboardButton(district))
                if len(current_row) == 2:
                    keyboard.append(current_row)
                    current_row = []
        
        # Додаємо останній неповний рядок, якщо він є
        if current_row:
            keyboard.append(current_row)
            
        # Додаємо кнопку "Інше" в окремий рядок
        keyboard.append([KeyboardButton('Інше')])
        
        # Додаємо кнопку "Назад"
        keyboard.append([KeyboardButton(BACK_BUTTON)])
        
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    except Exception as e:
        logger.error(f"Помилка при створенні клавіатури районів: {str(e)}")
        # Повертаємо просту клавіатуру з кнопкою "Назад" у випадку помилки
        return ReplyKeyboardMarkup([[KeyboardButton(BACK_BUTTON)]], resize_keyboard=True)

def create_summary_keyboard() -> ReplyKeyboardMarkup:
    """Створює клавіатуру для підсумкового меню"""
    keyboard = [
        [KeyboardButton("📅 Дізнатись час/дату")],
        [KeyboardButton(BACK_BUTTON)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def calculate_total_price(context: ContextTypes.DEFAULT_TYPE) -> tuple[int, list[str]]:
    """Підраховує загальну суму та формує список всіх виборів"""
    total_price = 0
    price_details = []
    
    try:
        # Отримуємо всі вибори користувача
        choices = context.user_data.get('choices', [])
        city = next((choice['value'] for choice in choices if choice['type'] == "Місто"), None)
        
        # Додаємо ціну за основну послугу (квест, пакет або погодинна оплата)
        for choice in choices:
            if choice['type'] == 'Квест':
                import re
                city = next((c['value'] for c in choices if c['type'] == "Місто"), None)
                
                try:
                    match = re.match(r"(.+?\(.*?\))\s*\((.*?)\)$", choice['value'])
                    if match:
                        quest_name = match.group(1).strip()
                        duration = match.group(2).strip()
                        price = QWEST[city][quest_name][duration]
                        total_price += price
                        price_details.append(f"🎮 Квест '{quest_name}' ({duration}): {price} грн")
                    else:
                        logger.error(f"Не вдалося розпарсити квест: {choice['value']}")
                        price_details.append(f"🎮 Квест '{choice['value']}': Ціна уточнюється")
                except Exception as e:
                    logger.error(f"Помилка при обробці ціни квесту: {str(e)}")
                    price_details.append(f"🎮 Квест '{choice['value']}': Ціна уточнюється")
                    
            elif choice['type'] == 'Пакет':
                try:
                    event_type = next((c['value'] for c in choices if c['type'] == "Тип події"), None)
                    if event_type:
                        price = PAKET_PRICES[city][event_type][choice['value']]
                        if isinstance(price, (int, float)):
                            total_price += price
                            price_details.append(f"📦 Пакет '{choice['value']}': {price} грн")
                        else:
                            price_details.append(f"📦 Пакет '{choice['value']}': {price}")
                except Exception as e:
                    logger.error(f"Помилка при обробці ціни пакету: {str(e)}")
                    price_details.append(f"📦 Пакет '{choice['value']}': Ціна уточнюється")
                    
            elif choice['type'] == 'Погодинна ціна':
                try:
                    price_info = choice['value'].split(' - ')
                    price_value = price_info[1]
                    if 'грн' in price_value:
                        try:
                            price = int(price_value.split()[0])
                            total_price += price
                            price_details.append(f"⏰ {price_info[0]}: {price} грн")
                        except ValueError:
                            price_details.append(f"⏰ {price_info[0]}: {price_value}")
                    else:
                        price_details.append(f"⏰ {price_info[0]}: {price_value}")
                except Exception as e:
                    logger.error(f"Помилка при обробці погодинної ціни: {str(e)}")
                    price_details.append(f"⏰ Погодинна ціна: Ціна уточнюється")
        
        # Додаємо ціни за додаткові послуги
        if 'additional_services' in context.user_data:
            for service, option in context.user_data['additional_services'].items():
                try:
                    # Підтримка формату: просто число з "грн" (наприклад, "4000 грн")
                    if isinstance(option, str) and option.strip().endswith('грн') and option.strip().replace(' грн', '').replace(' ', '').isdigit():
                        price = int(option.strip().split()[0])
                        total_price += price
                        price_details.append(f"➕ {service}: {option}")
                    elif ' - ' in option:
                        # Для шоу та інших послуг з форматом "НАЗВА - ЦІНА"
                        price_str = option.split(' - ')[1]
                        if 'грн' in price_str:
                            try:
                                price = int(price_str.split()[0])
                                total_price += price
                                price_details.append(f"➕ {service}: {option}")
                            except ValueError:
                                price_details.append(f"➕ {service}: {option}")
                        else:
                            price_details.append(f"➕ {service}: {option}")
                    else:
                        # Для майстер-класів та інших послуг з форматом "НАЗВА - ДЕТАЛІ - ЦІНА"
                        try:
                            # Розбиваємо рядок на частини
                            parts = option.split(' - ')
                            if len(parts) >= 2:
                                # Беремо останню частину як ціну
                                price_str = parts[-1]
                                if 'грн' in price_str:
                                    price = int(price_str.split()[0])
                                    total_price += price
                            price_details.append(f"➕ {service}: {option}")
                        except Exception as e:
                            logger.error(f"Помилка при обробці ціни для {service}: {str(e)}")
                            price_details.append(f"➕ {service}: {option}")
                except Exception as e:
                    logger.error(f"Помилка при обробці ціни додаткової послуги: {str(e)}")
                    price_details.append(f"➕ {service}: {option}")
        
        # Додаємо вартість таксі
        district = next((choice['value'] for choice in choices if choice['type'] == "Район"), None)
        if district and city:
            try:
                taxi_price = TAXI_PRICES[city][district]
                if isinstance(taxi_price, (int, float)):
                    total_price += taxi_price
                    price_details.append(f"🚕 Таксі ({district}): {taxi_price} грн")
                else:
                    price_details.append(f"🚕 Таксі ({district}): {taxi_price}")
            except Exception as e:
                logger.error(f"Помилка при обробці ціни таксі: {str(e)}")
                price_details.append(f"🚕 Таксі ({district}): Ціна уточнюється")
        
        return total_price, price_details
        
    except Exception as e:
        logger.error(f"Загальна помилка при підрахунку ціни: {str(e)}")
        return 0, ["❌ Помилка при підрахунку загальної вартості"]

# ============================================
# ОБРОБНИКИ ПОДІЙ
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Початок розмови та повернення до головного меню"""
    logger.info(f"[START] Викликано start для user_id={update.effective_user.id}, state={context.user_data}")
    user = update.effective_user
    
    # Очищаємо стан розмови
    context.user_data.clear()
    for key in ['choices', 'selected_city', 'additional_services', 'selected_service']:
        if key in context.user_data:
            del context.user_data[key]
    user_data.clear_conversation_state(user.id)
    
    # Зберігаємо базову інформацію про користувача
    old_user = user_data.get_user(user.id)
    old_phone = old_user.get('phone_number') if old_user else None
    old_device_info = old_user.get('device_info') if old_user else None
    old_visits = old_user.get('visits', 0) if old_user else 0
    old_order_count = old_user.get('order_count', 0) if old_user else 0
    visits = old_visits + 1
    user_info = get_unified_user_info(user, old_user, update)
    user_info['visits'] = visits
    user_data.add_user(user.id, user_info)
    
    # Скидаємо стару клавіатуру
    await update.message.reply_text(
        "Перезапуск меню...",
        reply_markup=ReplyKeyboardRemove()
    )
    # Відправляємо привітання з новою клавіатурою
    await update.message.reply_text(
        Hello_World,
        reply_markup=create_city_keyboard()
    )
    logger.info(f"[START] Завершено start для user_id={update.effective_user.id}")
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
    context.user_data['selected_city'] = city  # Зберігаємо місто для подальшого використання
    logger.info(f"[DEBUG] Поточні вибори після вибору міста: {context.user_data.get('choices')}")
    await save_state(update, context, CHOOSING_EVENT_TYPE)
    
    # Показуємо типи подій
    await update.message.reply_text(
        "Оберіть яку подію будете святкувати:",
        reply_markup=create_event_type_keyboard()
    )
    
    return CHOOSING_EVENT_TYPE

async def event_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору типу події"""
    try:
        event_type = update.message.text
        
        if event_type == BACK_BUTTON:
            remove_choice_by_type(context, 'Місто') 
            remove_choice_by_type(context, 'Тип події')  
            await update.message.reply_text(
                "Оберіть місто знову:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY

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
            add_choice(context, "Тип події", event_type)  # Додаємо цей рядок!
            await update.message.reply_text(
                GENERAL_INFO[city],
                reply_markup=create_other_keyboard()
            )
            return CHOOSING_EVENT_TYPE_inshe
        
        elif '👨‍👩‍👧‍👦 Сімейне свято' in event_type:
            city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                        if choice['type'] == "Місто"), None)
            
            if not city:
                await update.message.reply_text(
                    "Спочатку оберіть місто:",
                    reply_markup=create_city_keyboard()
                )
                return CHOOSING_CITY
                
            from config import FAMILY_INFO, FAMALY_TRIP
            add_choice(context, "Тип події", event_type)
            await update.message.reply_text(
                FAMILY_INFO,
                reply_markup=create_sim_svjata_keyboard_with_back(FAMALY_TRIP, city)
            )
            return CHOOSING_EVENT_TYPE_Sim_svjata
        
        # Для Дня народження та Випускного показуємо вибір локації
        elif '🎂 День народження' in event_type or '🎓 Випускний' in event_type:
            # Зберігаємо вибір типу події тільки для основних подій
            add_choice(context, "Тип події", event_type)
            await update.message.reply_text(
                "Оберіть місце де хотіли б святкувати:",
                reply_markup=create_location_keyboard(event_type)
            )
            return CHOOSING_LOCATION
        
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Помилка при обробці вибору типу події: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE

async def event_type_chosen_inshe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору в першому рівні розділу 'Інше'"""
    try:
        user_choice = update.message.text
        city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                    if choice['type'] == "Місто"), None)
        event_type = next((choice['value'] for choice in context.user_data.get('choices', []) 
                          if choice['type'] == "Тип події"), None)
        
        if not city or not event_type:
            logger.error("Місто або тип події не знайдено в виборах користувача")
            await update.message.reply_text(
                "Спочатку оберіть місто та тип події:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY

        if user_choice == BACK_BUTTON:
            remove_choice_by_type(context, 'Тип події')
            await update.message.reply_text(
                "Оберіть яку подію будете святкувати:",
                reply_markup=create_event_type_keyboard()
            )
            return CHOOSING_EVENT_TYPE

        elif user_choice == CONTACT_MANAGER_BUTTON:
            # Перевіряємо наявність міста перед відправкою контактів менеджера
            if not city or city not in MANAGER_INFO or city not in MANAGER_CONTACT_MESSAGES:
                await update.message.reply_text(
                    "Спочатку оберіть місто та тип події:",
                    reply_markup=create_city_keyboard()
                )
                return CHOOSING_CITY
            # Відправляємо контакти менеджера
            manager = MANAGER_INFO[city]
            message = MANAGER_CONTACT_MESSAGES[city].format(
                phone=manager['phone'],
                name=manager['name'],
                telegram=manager['telegram']
            )
            await update.message.reply_text(
                message,
                reply_markup=create_other_keyboard()
            )
            return CHOOSING_EVENT_TYPE_inshe
        
        # elif user_choice == "🎂 День народження":
        #     await update.message.reply_text(
        #         "Оберіть місце де хотіли б святкувати:",
        #         reply_markup=create_location_keyboard(user_choice)
        #     )
        #     return CHOOSING_LOCATION

    except Exception as e:
        logger.error(f"Помилка при обробці вибору в розділі 'Інше': {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_other_keyboard()
        )
        return CHOOSING_EVENT_TYPE_inshe

async def event_type_chosen__Sim_svjata(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору типу події для святкових подій"""
    text = update.message.text
    
    if text == BACK_BUTTON:
        remove_choice_by_type(context, 'Тип події')
        await update.message.reply_text(
            "Оберіть тип події знову:",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE

    # Підтримка всіх послуг із FAMALY_TRIP
    famaly_services = [f"{service} - {price} грн" for city_services in FAMALY_TRIP.values() for service, price in city_services.items()]
    if text in famaly_services:
        add_choice(context, 'Додаткова опція сімейної поїздки', text)
        context.user_data['service'] = text
        # Місто та тип події (з choices)
        if 'city' not in context.user_data:
            city = next((choice['value'] for choice in context.user_data.get('choices', []) if choice['type'] == "Місто"), None)
            if city is None:
                city = 'Невідомо'
            context.user_data['city'] = city
        if 'event_type' not in context.user_data:
            event_type = next((choice['value'] for choice in context.user_data.get('choices', []) if choice['type'] == "Тип події"), None)
            if event_type is None:
                event_type = 'Невідомо'
            context.user_data['event_type'] = event_type
        await update.message.reply_text(
            FAMILY_INFO_INFO2,
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton(CONTACT_MANAGER_BUTTON)],
                [KeyboardButton(BACK_BUTTON)]
            ], resize_keyboard=True)
        )
        return FFMILY_DOP
    else:
    # Якщо введено випадковий текст, просимо скористатися кнопками
        await update.message.reply_text(
            "Будь ласка, скористайтеся кнопками нижче.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton(option)] for option in famaly_services] + [[KeyboardButton(BACK_BUTTON)]],
                resize_keyboard=True
            )
        )
        return CHOOSING_EVENT_TYPE_Sim_svjata
    
    
    # elif text == "🎂 День народження":
    #     await update.message.reply_text(
    #         "Оберіть місце де хотіли б святкувати:",
    #         reply_markup=create_location_keyboard(text)
    #     )
    #     return CHOOSING_LOCATION
    
    # elif text == "🎓 Випускний":
    #     await update.message.reply_text(
    #         "Оберіть місце де хотіли б святкувати:",
    #         reply_markup=create_location_keyboard(text)
    #     )
    #     return CHOOSING_LOCATION

async def family_dop_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обробка вибору додаткової опції для сімейного свята : показує кнопки 'Зв'язатися з менеджером' і 'Назад'."""
        text = update.message.text
        add_choice(context, 'Додаткова опція сімейного свята', text)
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton(CONTACT_MANAGER_BUTTON)],
            [KeyboardButton(BACK_BUTTON)]
        ], resize_keyboard=True)
        text = update.message.text
        if text == CONTACT_MANAGER_BUTTON:
            # Збираємо деталі замовлення
            # Запам'ятати місто, тип події, послугу якщо ще не збережено
            if 'city' not in context.user_data:
                city = next((choice['value'] for choice in context.user_data.get('choices', []) if choice['type'] == "Місто"), 'Невідомо')
                context.user_data['city'] = city
            if 'event_type' not in context.user_data:
                event_type = next((choice['value'] for choice in context.user_data.get('choices', []) if choice['type'] == "Тип події"), 'Невідомо')
                context.user_data['event_type'] = event_type
            if 'service' not in context.user_data:
                context.user_data['service'] = text
            user = update.effective_user
            city = context.user_data.get('city', 'Невідомо')
            event_type = context.user_data.get('event_type', 'Сімейне свято')
            service = context.user_data.get('service', text)
            order_message = (
                f"Нове замовлення на сімейне свято!\n"
                f"Місто: {city}\n"
                f"Тип події: {event_type}\n"
                f"Послуга: {service}\n"
                f"Ім'я: {user.full_name}\n"
                f"Username: @{user.username if user.username else 'немає'}\n"
                f"User ID: {user.id}\n\n"
                "Замовлення сімейного свята\n"
            )
            await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=order_message)
            
            # Відповідь користувачу
            await update.message.reply_text(
                "Ваше замовлення надіслано менеджеру! Очікуйте дзвінка або повідомлення. Якщо бажаєте, можете залишити свій номер телефону для зв'язку:",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton('📱 Надіслати номер телефону', request_contact=True)],
                    [KeyboardButton('⬅️ На початок')]
                ], resize_keyboard=True)
            )
            return PHONE_CONTACT
            
        elif text == BACK_BUTTON:
            city = context.user_data.get('city', 'Невідомо')
            await update.message.reply_text(
                FAMILY_INFO,
                reply_markup=create_sim_svjata_keyboard_with_back(FAMALY_TRIP, city)
            )   
            return CHOOSING_EVENT_TYPE_Sim_svjata
        else:
            await update.message.reply_text(
                "Будь ласка, скористайтеся кнопками нижче.",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton(CONTACT_MANAGER_BUTTON)],
                    [KeyboardButton(BACK_BUTTON)]
                ], resize_keyboard=True)
            )
            return FFMILY_DOP


    
async def event_type_chosen_afisha(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору типу події для інших подій"""
    text = update.message.text
    
    if text == BACK_BUTTON:
        remove_choice_by_type(context, 'Тип події')
        remove_choice_by_type(context, 'Місто')
        await update.message.reply_text(
            "Оберіть тип події знову:",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
async def location_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору локації"""
    try:
        location = update.message.text
        
        # Отримуємо всі збережені вибори користувача
        user_choices = context.user_data.get('choices', [])
        logger.info(f"Поточні вибори користувача: {user_choices}")
        
        # Знаходимо останній збережений тип події
        event_type = None
        for choice in reversed(user_choices):
            if choice['type'] == "Тип події":
                event_type = choice['value']
                break
                
        city = next((choice['value'] for choice in user_choices 
                    if choice['type'] == "Місто"), None)
        
        if not city or not event_type:
            logger.error(f"Місто або тип події не знайдено в виборах користувача. Тип події: {event_type}, Місто: {city}")
            await update.message.reply_text(
                "Спочатку оберіть місто та тип події:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY

        if location == BACK_BUTTON:
            remove_choice_by_type(context, 'Локація')
            remove_choice_by_type(context, 'Тип події')
            await update.message.reply_text(
                "Оберіть яку подію будете святкувати:",
                reply_markup=create_event_type_keyboard()
            )
            return CHOOSING_EVENT_TYPE

        if location == '📍 Інше':
            # Створюємо клавіатуру для розділу "Інше"
            keyboard = [
                [KeyboardButton(SUGGEST_LOCATION_BUTTON)],
                [KeyboardButton(CONTACT_MANAGER_BUTTON)],
                [KeyboardButton(BACK_BUTTON)]
            ]
            await update.message.reply_text(
                "Чим саме я можу вам допомогти?",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return CHOOSING_LOCATION_inshe

        # Перевіряємо чи вибрана локація доступна для даного типу події
        available_locations = LOCATIONS.get(event_type, [])
        if not available_locations:
            logger.warning(f"Не знайдено локацій для типу події: {event_type}")
            available_locations = ['📍 Інше']  # Запасний варіант

        if location not in available_locations:
            await update.message.reply_text(
                "Будь ласка, оберіть локацію зі списку:",
                reply_markup=create_location_keyboard(event_type)
            )
            return CHOOSING_LOCATION

        # Зберігаємо вибір локації
        add_choice(context, "Локація", location)
        
        # Відправляємо інформацію про локацію
        location_info = LOCATION_INFO.get(city, {}).get(location, "Вибрана локація")
        await update.message.reply_text(
            f"Ви обрали локацію: {location}\n\n{location_info}\n\nТепер оберіть тематику свята:",
            reply_markup=create_theme_keyboard()
        )
        return CHOOSING_THEME

    except Exception as e:
        logger.error(f"Помилка при обробці вибору локації: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    
async def location_chosen_inshe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору в розділі 'Інше' (локації)"""
    try:
        user_choice = update.message.text
        city = next((choice['value'] for choice in context.user_data.get('choices', []) 
                    if choice['type'] == "Місто"), None)
        event_type = next((choice['value'] for choice in context.user_data.get('choices', []) 
                          if choice['type'] == "Тип події"), None)
        
        if not city or not event_type:
            logger.error("Місто або тип події не знайдено в виборах користувача")
            await update.message.reply_text(
                "Спочатку оберіть місто та тип події:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY

        if user_choice == BACK_BUTTON:
            await update.message.reply_text(
                "Оберіть місце де хотіли б святкувати:",
                reply_markup=create_location_keyboard(event_type)
            )
            return CHOOSING_LOCATION

        elif user_choice == CONTACT_MANAGER_BUTTON:
            # Перевіряємо наявність міста перед відправкою контактів менеджера
            if not city or city not in MANAGER_INFO or city not in MANAGER_CONTACT_MESSAGES:
                await update.message.reply_text(
                    "Спочатку оберіть місто та тип події:",
                    reply_markup=create_city_keyboard()
                )
                return CHOOSING_CITY
            # Відправляємо контакти менеджера
            manager = MANAGER_INFO[city]
            message = MANAGER_CONTACT_MESSAGES[city].format(
                phone=manager['phone'],
                name=manager['name'],
                telegram=manager['telegram']
            )
            await update.message.reply_text(
                message,
                reply_markup=create_location_keyboard(event_type)
            )
            return CHOOSING_LOCATION

        elif user_choice == SUGGEST_LOCATION_BUTTON:
            # Відправляємо PDF з підказками
            pdf_path = LOCATION_PDF_FILES.get(city)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as file:
                    await update.message.reply_document(
                        document=file,
                        caption=f"📍 Підказки щодо місць проведення у місті {city}",
                        reply_markup=create_location_keyboard(event_type)
                    )
            else:
                await update.message.reply_text(
                    "На жаль, файл з підказками тимчасово недоступний. "
                    "Будь ласка, зв'яжіться з менеджером для отримання інформації.",
                    reply_markup=create_location_keyboard(event_type)
                )
            return CHOOSING_LOCATION

        return CHOOSING_LOCATION_inshe

    except Exception as e:
        logger.error(f"Помилка при обробці вибору в розділі 'Інше': {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_location_keyboard(event_type)
        )
        return CHOOSING_LOCATION_inshe

async def theme_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору тематики свята"""
    try:
        theme = update.message.text
        
        # Отримуємо всі збережені вибори користувача
        user_choices = context.user_data.get('choices', [])
        logger.info(f"Поточні вибори користувача: {user_choices}")
        
        # Знаходимо останній збережений тип події та місто
        event_type = None
        for choice in reversed(user_choices):
            if choice['type'] == "Тип події":
                event_type = choice['value']
                break
                
        city = next((choice['value'] for choice in user_choices 
                    if choice['type'] == "Місто"), None)
        
        if not city or not event_type:
            logger.error(f"Місто або тип події не знайдено в виборах користувача. Тип події: {event_type}, Місто: {city}")
            await update.message.reply_text(
                "Спочатку оберіть місто та тип події:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY

        if theme == BACK_BUTTON:
            remove_choice_by_type(context, 'Тематика')
            # Знаходимо останню збережену локацію
            last_location = next((choice['value'] for choice in reversed(user_choices) 
                                if choice['type'] == "Локація"), None)
            if last_location:
                await update.message.reply_text(
                    "Оберіть місце де хотіли б святкувати:",
                    reply_markup=create_location_keyboard(event_type)
                )
            else:
                await update.message.reply_text(
                    "Оберіть місце де хотіли б святкувати:",
                    reply_markup=create_location_keyboard(event_type)
                )
            # Видаляємо значення локації
            remove_choice_by_type(context, 'Локація')
            return CHOOSING_LOCATION

        if theme == '📞 Зв\'язатись з менеджером':
            # Відправляємо контакти менеджера
            manager = MANAGER_INFO[city]
            message = MANAGER_CONTACT_MESSAGES[city].format(
                phone=manager['phone'],
                name=manager['name'],
                telegram=manager['telegram']
            )
            await update.message.reply_text(
                message,
                reply_markup=create_theme_keyboard()
            )
            return CHOOSING_THEME

        # Перевіряємо чи вибрана тематика доступна
        if theme not in THEMES:
            await update.message.reply_text(
                "Будь ласка, оберіть тематику зі списку:",
                reply_markup=create_theme_keyboard()
            )
            return CHOOSING_THEME

        # Зберігаємо вибір тематики (замість додавання ще однієї, видаляємо попередню)
        remove_choice_by_type(context, "Тематика")
        add_choice(context, "Тематика", theme)
        
        # Відправляємо інформацію про тематику та показуємо підтеми
        theme_info = THEME_INFO.get(theme, "")
        await update.message.reply_text(
            f"Ви обрали тематику: {theme}\n\n{theme_info}\n\nОберіть конкретну тематику:",
            reply_markup=create_theme2_keyboard(theme, city)
        )
        return CHOOSING_THEME2

    except Exception as e:
        logger.error(f"Помилка при обробці вибору тематики: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_theme_keyboard()
        )
        return CHOOSING_THEME

async def theme2_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору конкретної тематики"""
    try:
        subtheme = update.message.text
        
        # Отримуємо всі збережені вибори користувача
        user_choices = context.user_data.get('choices', [])
        logger.info(f"Поточні вибори користувача: {user_choices}")
        
        # Знаходимо останню збережену тематику
        theme = next((choice['value'] for choice in reversed(user_choices) 
                     if choice['type'] == "Тематика"), None)
        
        if not theme:
            logger.error("Тематика не знайдена в виборах користувача")
            await update.message.reply_text(
                "Спочатку оберіть тематику:",
                reply_markup=create_theme_keyboard()
            )
            return CHOOSING_THEME

        if subtheme == BACK_BUTTON:
            remove_choice_by_type(context, 'Підтема')
            await update.message.reply_text(
                "Оберіть тематику:",
                reply_markup=create_theme_keyboard()
            )
            return CHOOSING_THEME

        # Перевіряємо чи вибрана підтема доступна для даної тематики
        city = next((choice['value'] for choice in user_choices if choice['type'] == "Місто"), None)
        if not city:
            logger.error("Не вдалося визначити місто для вибору підтеми")
            await update.message.reply_text(
                "Помилка: не знайдено місто. Почніть з початку.",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
        
        available_subthemes = THEME_BTN.get(city, {}).get(theme, [])
        if subtheme not in available_subthemes:
            await update.message.reply_text(
                "Будь ласка, оберіть тематику зі списку:",
                reply_markup=create_theme2_keyboard(theme, city)
            )
            return CHOOSING_THEME2

        # Зберігаємо вибір підтеми
        add_choice(context, "Підтема", subtheme)
        
        # --- Додаємо отримання міста для фото підтеми ---
        city = next((choice['value'] for choice in user_choices if choice['type'] == "Місто"), None)
        # Отримуємо посилання на фото для підтеми з урахуванням міста
        photo_url = None
        if city:
            photo_url = THEME_PHOTOS.get(city, {}).get(theme, {}).get(subtheme)
        
        # Відправляємо фото з описом
        if photo_url:
            if os.path.exists(photo_url):
                with open(photo_url, 'rb') as photo:
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"🎨 {subtheme}\n\nОберіть опцію:",
                        reply_markup=create_theme_details_keyboard()
                    )
            else:
                await update.message.reply_photo(
                    photo=photo_url,
                    caption=f"🎨 {subtheme}\n\nОберіть опцію:",
                    reply_markup=create_theme_details_keyboard()
                )
        else:
            await update.message.reply_text(
                f"🎨 {subtheme}\n\nОберіть опцію:",
                reply_markup=create_theme_details_keyboard()
            )
        
        return CHOOSING_THEME_DETAILS

    except Exception as e:
        logger.error(f"Помилка при обробці вибору підтеми: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_theme_keyboard()
        )
        return CHOOSING_THEME

async def theme_details_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору в деталях теми"""
    try:
        choice = update.message.text
        
        # Отримуємо всі збережені вибори користувача
        user_choices = context.user_data.get('choices', [])
        logger.info(f"Поточні вибори користувача: {user_choices}")
        
        # Знаходимо останню збережену тематику та підтему
        theme = next((choice['value'] for choice in reversed(user_choices) 
                     if choice['type'] == "Тематика"), None)
        subtheme = next((choice['value'] for choice in reversed(user_choices) 
                        if choice['type'] == "Підтема"), None)
        
        if not theme:
            logger.error("Тематика не знайдена в виборах користувача")
            await update.message.reply_text(
                "Спочатку оберіть тематику:",
                reply_markup=create_theme_keyboard()
            )
            return CHOOSING_THEME

        if choice == BACK_BUTTON:
            # Видаляємо останню підтему
            remove_choice_by_type(context, 'Підтема')
            # Отримуємо оновлений список виборів
            user_choices = context.user_data.get('choices', [])
            # Знаходимо тему знову
            theme = next((choice['value'] for choice in reversed(user_choices) 
                         if choice['type'] == "Тематика"), None)
            
            city = next((choice['value'] for choice in user_choices if choice['type'] == "Місто"), None)
            if not city:
                logger.error("Не вдалося визначити місто у theme_details_chosen")
                await update.message.reply_text(
                    "Помилка: не знайдено місто. Почніть з початку.",
                    reply_markup=create_city_keyboard()
                )
                return CHOOSING_CITY
            await update.message.reply_text(
                "Оберіть конкретну тематику:",
                reply_markup=create_theme2_keyboard(theme, city)
            )
            return CHOOSING_THEME2
        
        if choice == "💰 Ціни":
            # Відправляємо повідомлення про недоступність цін
            await update.message.reply_text(
                "💰 Інформація про ціни тимчасово недоступна. "
                "Будь ласка, зв'яжіться з менеджером для отримання детальної інформації.",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT

        return CHOOSING_THEME_DETAILS

    except Exception as e:
        logger.error(f"Помилка при обробці вибору в деталях теми: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_theme_keyboard()
        )
        return CHOOSING_THEME
    
async def format_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вибір формату свята"""
    text = update.message.text
    
    # Отримуємо всі збережені вибори користувача
    user_choices = context.user_data.get('choices', [])
    logger.info(f"Поточні вибори користувача: {user_choices}")
    
    # Знаходимо місто та тип події
    city = next((choice['value'] for choice in user_choices 
                if choice['type'] == "Місто"), None)
    event_type = next((choice['value'] for choice in user_choices 
                      if choice['type'] == "Тип події"), None)
    
    # Знаходимо вибрану локацію
    location = next((choice['value'] for choice in user_choices 
                    if choice['type'] == "Локація"), None)
    
    if text == BACK_BUTTON:
        # Повертаємося до деталей теми
        theme = next((choice['value'] for choice in reversed(user_choices) 
                     if choice['type'] == "Тематика"), None)
        subtheme = next((choice['value'] for choice in reversed(user_choices) 
                        if choice['type'] == "Підтема"), None)
        
        if subtheme:
            # --- Додаємо отримання міста для фото підтеми (BACK_BUTTON) ---
            city = next((choice['value'] for choice in user_choices if choice['type'] == "Місто"), None)
            photo_url = None
            if city:
                photo_url = THEME_PHOTOS.get(city, {}).get(theme, {}).get(subtheme)
            # Відправляємо фото з описом
            if photo_url:
                if os.path.exists(photo_url):
                    with open(photo_url, 'rb') as photo:
                        await update.message.reply_photo(
                            photo=photo,
                            caption=f"🎨 {subtheme}\n\nОберіть опцію:",
                            reply_markup=create_theme_details_keyboard()
                        )
                else:
                    await update.message.reply_photo(
                        photo=photo_url,
                        caption=f"🎨 {subtheme}\n\nОберіть опцію:",
                        reply_markup=create_theme_details_keyboard()
                    )
            else:
                await update.message.reply_text(
                    f"🎨 {subtheme}\n\nОберіть опцію:",
                    reply_markup=create_theme_details_keyboard()
                )
            return CHOOSING_THEME_DETAILS
        else:
            # Якщо підтеми немає, повертаємося до вибору підтеми
            await update.message.reply_text(
                "Оберіть конкретну тематику:",
                reply_markup=create_theme2_keyboard(theme, city)
            )
            return CHOOSING_THEME2
    
    # Зберігаємо вибраний формат
    add_choice(context, "Формат", text)
    
    # Якщо вибрано погодинний формат
    if text == "⏰ Погодинно":
        # Перевіряємо, чи це випускний або день народження
        if event_type in ["🎂 День народження", "🎓 Випускний"]:
            # Перевіряємо, чи це заміський комплекс
            is_tourbase = location and "🏰 Заміський комплекс" in location
            
            # Визначаємо ключ для цін
            price_key = event_type
            if is_tourbase:
                price_key = f"{event_type} (турбаза)"
            
            # Показуємо погодинні ціни
            await update.message.reply_text(
                f"💰 Погодинні ціни для {event_type} у місті {city}\n\n" + 
                ("❗️УВАГА! Формування замовлення, для святкування в заміському комплексі, передбачає тривалість свята мінімум від двох годин" if is_tourbase else "") + ":",
                reply_markup=create_hourly_price_keyboard(city, price_key)
            )
            return CHOOSING_HOURLY_PRICE
        else:
            # Для інших типів подій
            await update.message.reply_text(
                "Для цього типу події погодинні ціни не доступні. "
                "Будь ласка, зв'яжіться з менеджером для отримання інформації.",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT
    
    # Якщо вибрано погодинний формат
    if text == "📦 Пакетні пропозиції":
        # Перевіряємо, чи це випускний або день народження
        if event_type in ["🎂 День народження", "🎓 Випускний"]:
            # Показуємо пакетні пропозиції
            await update.message.reply_text(
                f"📦 Пакетні пропозиції для {event_type} у місті {city}:",
                reply_markup=create_package_keyboard(city, event_type)
            )
            return CHOOSING_PACKAGE
        else:
            await update.message.reply_text(
                "Для цього типу події пакетні пропозиції не доступні.",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT
            
    elif text == "🎯 Квести":
        # Показуємо квести
        await update.message.reply_text(
            f"🎮 Доступні квести у місті {city}:",
            reply_markup=create_qwest_keyboard(city)
        )
        return CHOOSING_QWEST
        
    return CHOOSING_FORMAT

async def hourly_price_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вибір погодинної ціни"""
    try:
        text = update.message.text
        
        # Отримуємо всі збережені вибори користувача
        user_choices = context.user_data.get('choices', [])
        logger.info(f"Поточні вибори користувача: {user_choices}")
        
        # Знаходимо місто та тип події
        city = next((choice['value'] for choice in user_choices 
                    if choice['type'] == "Місто"), None)
        event_type = next((choice['value'] for choice in user_choices 
                          if choice['type'] == "Тип події"), None)
        
        # Знаходимо вибрану локацію
        location = next((choice['value'] for choice in user_choices 
                        if choice['type'] == "Локація"), None)
        
        # Перевіряємо, чи це заміський комплекс
        is_tourbase = location and "🏰 Заміський комплекс" in location
        
        # Визначаємо ключ для цін
        price_key = event_type
        if is_tourbase:
            price_key = f"{event_type} (турбаза)"
        
        if not city or not event_type:
            logger.error("Місто або тип події не знайдено в виборах користувача")
            await update.message.reply_text(
                "Спочатку оберіть місто та тип події:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY

        if text == BACK_BUTTON:
            # Повертаємося до вибору формату
            await update.message.reply_text(
                "Оберіть формат свята:",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT

        if text == CONTACT_MANAGER_BUTTON:
            # Відправляємо контакти менеджера
            manager = MANAGER_INFO[city]
            message = MANAGER_CONTACT_MESSAGES[city].format(
                phone=manager['phone'],
                name=manager['name'],
                telegram=manager['telegram']
            )
            await update.message.reply_text(
                message,
                reply_markup=create_hourly_price_keyboard(city, price_key)
            )
            return CHOOSING_HOURLY_PRICE

        # Якщо користувач вибрав ціну
        if ":" in text:
            price_name = text.split(":")[0].strip()
            price_value = text.split(":")[1].strip()
            
            # Зберігаємо вибір ціни
            add_choice(context, "Погодинна ціна", f"{price_name} - {price_value}")
            
            # Додаємо інформацію про мінімальну тривалість для заміського комплексу
            min_duration_info = ""
            if is_tourbase:
                min_duration_info = "\n❗️ Для заміського комплексу мінімальна тривалість - 2 години."
            
            # Відправляємо повідомлення про вибір
            await update.message.reply_text(
                f"Ви обрали: {price_name}\n"
                f"Вартість: {price_value}\n"
                f"{min_duration_info}\n\n"
                "Для уточнення деталей та бронювання, будь ласка, зв'яжіться з менеджером."
            )
            
            # Показуємо фінальне меню формату   
            await update.message.reply_text(
                "Чи сподобався вам цей варіант?",
                reply_markup=create_final_keyboard()
            )
            return CHOOSING_FINAL

        return CHOOSING_HOURLY_PRICE

    except Exception as e:
        logger.error(f"Помилка при обробці вибору погодинної ціни: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_format_keyboard()
        )
        return CHOOSING_FORMAT

async def package_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вибір пакету"""
    text = update.message.text
    
    if text == BACK_BUTTON:
        # Видаляємо останній формат, якщо він є
        remove_choice_by_type(context, 'Формат')
        remove_choice_by_type(context, 'Пакет')
        await update.message.reply_text(
            "Оберіть формат свята:",
            reply_markup=create_format_keyboard()
        )
        return CHOOSING_FORMAT
    
    try:
        # Отримуємо всі збережені вибори користувача
        user_choices = context.user_data.get('choices', [])
        logger.info(f"Поточні вибори користувача: {user_choices}")
        
        # Знаходимо місто та тип події
        city = next((choice['value'] for choice in user_choices 
                    if choice['type'] == "Місто"), None)
        event_type = next((choice['value'] for choice in user_choices 
                          if choice['type'] == "Тип події"), None)
        
        if not city or not event_type:
            logger.error("Місто або тип події не знайдено в виборах користувача")
            await update.message.reply_text(
                "Спочатку оберіть місто та тип події:",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
        
        # Зберігаємо вибраний пакет
        add_choice(context, "Пакет", text)
        
        # Отримуємо ціну пакету
        price = PAKET_PRICES[city][event_type][text]
        
        # Отримуємо шлях до фото пакету
        photo_path = PAKET_PHOTOS[city][event_type][text]
        
        # Перевіряємо наявність файлу
        if os.path.exists(photo_path):
            # Відправляємо фото пакету
            with open(photo_path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"🎉 Вибрано пакет: {text}\n💰 Вартість: {price} грн\n\n"
                            f"Для замовлення цього пакету зв'яжіться з нашим менеджером:"
                )
        else:
            # Якщо файл не знайдено, відправляємо повідомлення без фото
            logger.warning(f"Файл не знайдено: {photo_path}")
            await update.message.reply_text(
                f"🎉 Вибрано пакет: {text}\n💰 Вартість: {price} грн\n\n"
                f"Для замовлення цього пакету зв'яжіться з нашим менеджером:"
            )
            
        # Показуємо фінальне меню
        await update.message.reply_text(
            "Чи сподобався вам цей варіант?",
            reply_markup=create_final_keyboard()
        )
        return CHOOSING_FINAL
        
    except Exception as e:
        logger.error(f"Помилка при обробці вибору пакету: {str(e)}")
        await update.message.reply_text(
            "Вибачте, сталася помилка. Спробуйте ще раз або зверніться до менеджера."
        )
        return ConversationHandler.END
    

async def qwest_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вибір квесту"""
    try:
        text = update.message.text
        
        if text == BACK_BUTTON:
            # Видаляємо останній формат, якщо він є
            remove_choice_by_type(context, 'Формат')
            remove_choice_by_type(context, 'Пакет')
            remove_choice_by_type(context, 'Квест')  # Додаємо видалення вибору квесту
            if 'selected_qwest' in context.user_data:
                del context.user_data['selected_qwest']
            # Повертаємося до вибору формату
            await update.message.reply_text(
                "Оберіть формат свята:",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT
            
        # Отримуємо місто з виборів користувача
        user_choices = context.user_data.get('choices', [])
        city = next((choice['value'] for choice in user_choices 
                    if choice['type'] == "Місто"), None)
                    
        if not city:
            await update.message.reply_text("Будь ласка, спочатку виберіть місто.")
            return ConversationHandler.END
            
        # Зберігаємо вибраний квест та місто
        context.user_data['selected_qwest'] = text
        context.user_data['selected_city'] = city
        
        # Отримуємо шлях до фото
        photo_path = QWEST_PHOTOS.get(text)
        
        # Надсилаємо фото, якщо воно існує
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"🎮 Вибрано квест: {text}\n\n"
                            f"Оберіть тривалість квесту:",
                    reply_markup=create_qwest_duration_keyboard(text, city)
                )
        else:
            await update.message.reply_text(
                f"🎮 Вибрано квест: {text}\n\nОберіть тривалість квесту:",
                reply_markup=create_qwest_duration_keyboard(text, city)
            )
        return CHOOSING_QWEST_DURATION
        
    except Exception as e:
        logger.error(f"Помилка при обробці вибору квесту: {str(e)}")
        await update.message.reply_text(
            "Вибачте, сталася помилка. Спробуйте ще раз або зверніться до менеджера.",
            reply_markup=create_theme_details_keyboard()
        )
        return CHOOSING_THEME

async def qwest_duration_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вибір тривалості квесту"""
    try:
        text = update.message.text
        
        if text == BACK_BUTTON:
            # Повертаємося до вибору квесту
            city = context.user_data.get('selected_city')
            if not city:
                # Якщо місто не знайдено в context.user_data, пробуємо знайти в choices
                city = next((choice['value'] for choice in user_choices 
                           if choice['type'] == "Місто"), None)
            
            if not city:
                await update.message.reply_text("Будь ласка, спочатку виберіть місто.")
                return ConversationHandler.END
                
            await update.message.reply_text(
                f"🎮 Доступні квести у місті {city}:",
                reply_markup=create_qwest_keyboard(city)
            )
            return CHOOSING_QWEST
            
        # Отримуємо збережені дані
        city = context.user_data.get('selected_city')
        qwest_name = context.user_data.get('selected_qwest')
        
        if not city or not qwest_name:
            await update.message.reply_text("Будь ласка, почніть спочатку.")
            return ConversationHandler.END
            
        # Розбираємо текст для отримання тривалості та ціни
        duration, price = text.split(" - ")
        price = int(price.split()[0])  # Видаляємо "грн" і конвертуємо в число
        
        # Зберігаємо вибір
        add_choice(context, "Квест", f"{qwest_name} ({duration})")
        
        # Відправляємо повідомлення з інформацією про вибір
        await update.message.reply_text(
            f"🎮 Вибрано квест: {qwest_name}\n"
            f"⏱ Тривалість: {duration}\n"
            f"💰 Вартість: {price} грн\n\n"
            f"Для замовлення цього квесту зв'яжіться з нашим менеджером:"
        )
            
        # Показуємо фінальне меню
        await update.message.reply_text(
            "Чи сподобався вам цей варіант?",
            reply_markup=create_final_keyboard()
        )
        return CHOOSING_FINAL
        
    except Exception as e:
        logger.error(f"Помилка при обробці вибору тривалості квесту: {str(e)}")
        await update.message.reply_text(
            "Вибачте, сталася помилка. Спробуйте ще раз або зверніться до менеджера."
        )
        return ConversationHandler.END

async def final_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє фінальний вибір"""
    text = update.message.text
    
    if text == BACK_BUTTON:
        # Отримуємо останній вибір
        user_choices = context.user_data.get('choices', [])
        last_choice = next((choice for choice in reversed(user_choices) 
                          if choice['type'] in ['Квест', 'Пакет', 'Погодинна ціна']), None)
        
        if not last_choice:
            await update.message.reply_text(
                "Оберіть формат свята:",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT
            
        # Видаляємо останній вибір
        remove_choice_by_type(context, last_choice['type'])
        
        # Повертаємося до відповідного стану
        if last_choice['type'] == 'Квест':
            city = context.user_data.get('selected_city')
            if not city:
                # Якщо місто не знайдено в context.user_data, пробуємо знайти в choices
                city = next((choice['value'] for choice in user_choices 
                           if choice['type'] == "Місто"), None)
            
            if not city:
                await update.message.reply_text("Будь ласка, спочатку виберіть місто.")
                return ConversationHandler.END
                
            # Зберігаємо місто в context.user_data для подальшого використання
            context.user_data['selected_city'] = city
                
            await update.message.reply_text(
                f"🎮 Доступні квести у місті {city}:",
                reply_markup=create_qwest_keyboard(city)
            )
            return CHOOSING_QWEST
        elif last_choice['type'] == 'Пакет':
            await update.message.reply_text(
                "Оберіть формат свята:",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT
        elif last_choice['type'] == 'Погодинна ціна':
            await update.message.reply_text(
                "Оберіть формат свята:",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT
            
    elif text == WOW_BUTTON:
        # Показуємо меню додаткових послуг
        city = context.user_data.get('selected_city')
        if not city:
            # Якщо місто не знайдено в context.user_data, пробуємо знайти в choices
            user_choices = context.user_data.get('choices', [])
            city = next((choice['value'] for choice in user_choices 
                        if choice['type'] == "Місто"), None)
            
            if not city:
                await update.message.reply_text("Будь ласка, спочатку виберіть місто.")
                return ConversationHandler.END
                
            # Зберігаємо місто в context.user_data для подальшого використання
            context.user_data['selected_city'] = city
            
        await update.message.reply_text(
            "Оберіть додаткові послуги:",
            reply_markup=create_additional_services_keyboard(city, context)
        )
        return CHOOSING_ADDITIONAL_SERVICES
        
    return CHOOSING_FINAL

async def additional_services_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє вибір додаткової послуги"""
    try:
        text = update.message.text
        city = context.user_data.get('selected_city')
        
        # Логуємо поточний стан та вибір користувача
        logger.info(f"Отримано текст: {text}")
        logger.info(f"Поточне місто: {city}")
        logger.info(f"Поточний стан context.user_data: {context.user_data}")
        
        if not city:
            logger.warning("Місто не знайдено в context.user_data")
            await update.message.reply_text(
                "Будь ласка, спочатку виберіть місто.",
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY
        
        if text == BACK_BUTTON:
            logger.info("Натиснуто кнопку НАЗАД")
            # Якщо ми в режимі видалення послуг
            if context.user_data.get('removing_services'):
                logger.info("Виходимо з режиму видалення послуг")
                del context.user_data['removing_services']
                await update.message.reply_text(
                    "Оберіть додаткові послуги:",
                    reply_markup=create_additional_services_keyboard(city, context)
                )
                return CHOOSING_ADDITIONAL_SERVICES
            # Якщо ми в режимі вибору опції послуги
            elif 'selected_service' in context.user_data:
                logger.info(f"Видаляємо вибрану послугу: {context.user_data['selected_service']}")
                del context.user_data['selected_service']
                await update.message.reply_text(
                    "Оберіть додаткові послуги:",
                    reply_markup=create_additional_services_keyboard(city, context)
                )
                return CHOOSING_ADDITIONAL_SERVICES
            # Якщо ми в режимі вибору послуг
            else:
                logger.info("Повертаємось до вибору формату та очищуємо додаткові послуги")
                # Очищаємо всі вибрані додаткові послуги
            if 'additional_services' in context.user_data:
                logger.info(f"Видаляємо всі додаткові послуги: {context.user_data['additional_services']}")
                del context.user_data['additional_services']
                # Універсально очищаємо всі вибори після останнього 'Формат'
                choices = context.user_data.get('choices', [])
                last_format_idx = None
                for i in range(len(choices)-1, -1, -1):
                    if choices[i]['type'] == 'Формат':
                        last_format_idx = i
                        break
                if last_format_idx is not None:
                    context.user_data['choices'] = choices[:last_format_idx]
                # Очищаємо всі залежні ключі
                for k in ['selected_qwest', 'selected_paket', 'selected_hourly']:
                    if k in context.user_data:
                        del context.user_data[k]
            await update.message.reply_text(
                "Оберіть формат свята:",
                reply_markup=create_format_keyboard()
            )
            return CHOOSING_FORMAT
            
        # Якщо натиснуто "Показати вибрані послуги"
        if text == SHOW_SELECTED_SERVICES_BUTTON:
            logger.info("Показуємо меню видалення послуг")
            context.user_data['removing_services'] = True
            await update.message.reply_text(
                "Виберіть послугу для видалення:",
                reply_markup=create_selected_services_keyboard(context, city)
            )
            return CHOOSING_ADDITIONAL_SERVICES
            
        # Перевіряємо чи це видалення конкретної послуги
        if text.startswith("❌ ") and context.user_data.get('removing_services'):
            # Видаляємо префікс ❌ та розділяємо на сервіс і опцію
            service = text[2:].split(":")[0].strip()
            logger.info(f"Видаляємо послугу: {service}")
            
            if 'additional_services' in context.user_data and service in context.user_data['additional_services']:
                del context.user_data['additional_services'][service]
                logger.info(f"Послугу {service} видалено")
                
                # Якщо всі послуги видалені, повертаємося до звичайного меню
                if not context.user_data['additional_services']:
                    del context.user_data['additional_services']
                    del context.user_data['removing_services']
                    await update.message.reply_text(
                        "Всі послуги видалено. Оберіть нові послуги:",
                        reply_markup=create_additional_services_keyboard(city, context)
                    )
                else:
                    await update.message.reply_text(
                        f"Послугу {service} видалено. Виберіть іншу послугу для видалення:",
                        reply_markup=create_selected_services_keyboard(context, city)
                    )
                return CHOOSING_ADDITIONAL_SERVICES
            
        if text == NEXT_BUTTON:
            logger.info("[ADDITIONAL_SERVICES] Натиснуто 'Далі'.")
            # Перевіряємо наявність вибраних послуг
            if 'additional_services' not in context.user_data:
                logger.warning("[ADDITIONAL_SERVICES] Вибрані послуги відсутні.")
                message = "❗️ Ви не вибрали жодної додаткової послуги.\n\n"
            else:
                # Формуємо повідомлення з вибраними послугами
                message = "🎉 Ваші вибрані додаткові послуги:\n\n"
                for service, option in context.user_data['additional_services'].items():
                    message += f"• {service}: {option}\n"
            
            message += "\n🚕 Будь ласка, оберіть ваш район для розрахунку вартості таксі:"
            
            # Показуємо повідомлення з вибраними послугами та клавіатуру з районами
            await update.message.reply_text(
                message,
                reply_markup=create_district_keyboard(city)
            )
            return CHOOSING_DISTRICT
            
        # Якщо вибрано послугу з підменю
        if city in ADDITIONAL_SERVICES_WITH_SUBMENU and text in ADDITIONAL_SERVICES_WITH_SUBMENU[city]:
            logger.info(f"[ADDITIONAL_SERVICES] Вибрано послугу з підменю: {text}")
            await update.message.reply_text(
                f"Виберіть опцію для послуги '{text}':",
                reply_markup=create_service_options_keyboard(city, text)
            )
            context.user_data['selected_service'] = text
            logger.info(f"[ADDITIONAL_SERVICES] Збережено вибрану послугу: {text}")
            return CHOOSING_SERVICE_OPTION
            
        # Якщо вибрано просту послугу
        if city in ADDITIONAL_SERVICES_SINGLE:
            # Отримуємо назву послуги без ціни
            service_name = text.split(" - ")[0].strip() if " - " in text else text
            logger.info(f"[ADDITIONAL_SERVICES] Перевіряємо просту послугу: {service_name}")
            
            # Перевіряємо чи є така послуга в списку простих послуг
            if service_name in ADDITIONAL_SERVICES_SINGLE[city]:
                logger.info(f"[ADDITIONAL_SERVICES] Знайдено просту послугу: {service_name}")
                price = ADDITIONAL_SERVICES_SINGLE[city][service_name]
                if isinstance(price, str):
                    price_text = price
                else:
                    price_text = f"{price} грн"
                    
                if 'additional_services' not in context.user_data:
                    context.user_data['additional_services'] = {}
                # Зберігаємо тільки ціну як значення
                context.user_data['additional_services'][service_name] = price_text
                logger.info(f"[ADDITIONAL_SERVICES] Додано просту послугу: {service_name} = {price_text}")
                
                # Перевіряємо, чи є фото для генератора мильних бульбашок
                if service_name == '🫧 Генератор мильних бульбашок':
                    # Знаходимо ключ міста
                    city_key = None
                    normalized_city = city.replace('-', '').replace(' ', '').upper()
                    for ck in ADDITIONAL_SERVICES_PHOTOS.keys():
                        if ck.replace('-', '').replace(' ', '').upper() == normalized_city:
                            city_key = ck
                            break
                    if city_key and "ГЕНЕРАТОР" in ADDITIONAL_SERVICES_PHOTOS[city_key]:
                        photo_path = ADDITIONAL_SERVICES_PHOTOS[city_key]["ГЕНЕРАТОР"].get(service_name)
                        logger.info(f"[ADDITIONAL_SERVICES] Шлях до фото генератора: {photo_path}")
                        if photo_path and os.path.exists(photo_path):
                            logger.info(f"[ADDITIONAL_SERVICES] Файл {photo_path} існує")
                            await update.message.reply_photo(
                                photo=open(photo_path, 'rb'),
                                caption=f"Послугу '{service_name}' додано до вашого вибору.\nВартість: {price_text}",
                                reply_markup=create_additional_services_keyboard(city, context)
                            )
                        else:
                            logger.warning(f"[ADDITIONAL_SERVICES] Файл {photo_path} не існує або не знайдено")
                            await update.message.reply_text(
                                f"Послугу '{service_name}' додано до вашого вибору.\nВартість: {price_text}",
                                reply_markup=create_additional_services_keyboard(city, context)
                            )
                    else:
                        logger.warning(f"[ADDITIONAL_SERVICES] Не знайдено фото для генератора у місті {city}")
                        await update.message.reply_text(
                            f"Послугу '{service_name}' додано до вашого вибору.\nВартість: {price_text}",
                            reply_markup=create_additional_services_keyboard(city, context)
                        )
            
        # Якщо вибрано опцію послуги
        if 'selected_service' in context.user_data:
            service = context.user_data['selected_service']
            logger.info(f"[ADDITIONAL_SERVICES] Обробка опції для послуги: {service}")
            if city in ADDITIONAL_SERVICES_WITH_SUBMENU and service in ADDITIONAL_SERVICES_WITH_SUBMENU[city]:
                options = ADDITIONAL_SERVICES_WITH_SUBMENU[city][service]
                for option, price in options.items():
                    if text.startswith(option):
                        logger.info(f"[ADDITIONAL_SERVICES] Знайдено відповідну опцію: {text}")
                        if 'additional_services' not in context.user_data:
                            context.user_data['additional_services'] = {}
                        context.user_data['additional_services'][service] = text
                        del context.user_data['selected_service']
                        logger.info(f"[ADDITIONAL_SERVICES] Збережено вибір опції та видалено selected_service")
                        
                        # Визначаємо категорію послуги та знаходимо відповідне фото
                        photo_path = None
                        option_name = option.split(" - ")[0].strip()
                        logger.info(f"[ADDITIONAL_SERVICES] Опція для пошуку фото: {option_name}")
                        
                        # --- НОВА логіка пошуку фото з урахуванням міста як ключа ---
                        city_key = None
                        normalized_city = city.replace('-', '').replace(' ', '').upper()
                        for ck in ADDITIONAL_SERVICES_PHOTOS.keys():
                            if ck.replace('-', '').replace(' ', '').upper() == normalized_city:
                                city_key = ck
                                break
                        if not city_key:
                            logger.error(f"[ADDITIONAL_SERVICES] Не знайдено місто '{city}' у ADDITIONAL_SERVICES_PHOTOS")
                            await update.message.reply_text("Фото для цієї послуги не знайдено (місто)")
                            return CHOOSING_ADDITIONAL_SERVICES

                        # 2. Знаходимо тип послуги (ШОУ, МАЙСТЕР-КЛАС...) у цьому місті
                        service_type = None
                        for key in ADDITIONAL_SERVICES_PHOTOS[city_key]:
                            if key.upper() in service.upper() or service.upper() in key.upper():
                                service_type = key
                                break
                        if not service_type:
                            normalized_service = service.replace('-', '').replace(' ', '').upper()
                            for key in ADDITIONAL_SERVICES_PHOTOS[city_key]:
                                if key.replace('-', '').replace(' ', '').upper() in normalized_service or normalized_service in key.replace('-', '').replace(' ', '').upper():
                                    service_type = key
                                    break
                        # Додатковий хак для "ГЕНЕРАТОРА"
                        if not service_type:
                            if "ГЕНЕРАТОР" in service.upper() or "БУЛЬБАШОК" in service.upper():
                                service_type = "ГЕНЕРАТОР"
                            else:
                                logger.error(f"[ADDITIONAL_SERVICES] Не знайдено тип послуги '{service}' для міста '{city_key}'")
                                await update.message.reply_text("Фото для цієї послуги не знайдено (тип)")
                                return CHOOSING_ADDITIONAL_SERVICES

                        # 3. Шукаємо фото по назві опції
                        photo_dict = ADDITIONAL_SERVICES_PHOTOS[city_key][service_type]
                        base_name = option_name.split('-')[0].strip().upper()
                        photo_path = None
                        for name in photo_dict:
                            if name.upper() in base_name or base_name in name.upper():
                                photo_path = photo_dict[name]
                                break

                        if photo_path:
                            logger.info(f"[ADDITIONAL_SERVICES] Знайдено шлях до фото: {photo_path}")
                            if os.path.exists(photo_path):
                                logger.info(f"[ADDITIONAL_SERVICES] Файл {photo_path} існує")
                                await update.message.reply_photo(
                                    photo=open(photo_path, 'rb'),
                                    caption=f"Опцію '{text}' для послуги '{service}' додано до вашого вибору.",
                                    reply_markup=create_additional_services_keyboard(city, context)
                                )
                            else:
                                logger.warning(f"[ADDITIONAL_SERVICES] Файл {photo_path} не існує")
                                await update.message.reply_text(
                                    f"Опцію '{text}' для послуги '{service}' додано до вашого вибору.",
                                    reply_markup=create_additional_services_keyboard(city, context)
                                )
                        else:
                            logger.warning(f"[ADDITIONAL_SERVICES] Не знайдено шлях до фото для опції {option_name}")
                            await update.message.reply_text(
                                f"Опцію '{text}' для послуги '{service}' додано до вашого вибору.",
                                reply_markup=create_additional_services_keyboard(city, context)
                            )
                        return CHOOSING_ADDITIONAL_SERVICES
                            
        logger.warning(f"[ADDITIONAL_SERVICES] Отримано неочікуваний текст: {text}")
        await update.message.reply_text(
            "Будь ласка, використовуйте кнопки для вибору опції.",
            reply_markup=create_additional_services_keyboard(city, context)
        )
        return CHOOSING_ADDITIONAL_SERVICES
        
    except Exception as e:
        logger.error(f"[ADDITIONAL_SERVICES] Помилка при обробці вибору додаткової послуги: {str(e)}")
        logger.exception(e)  # Додаємо повний стек помилки
        await update.message.reply_text(
            "Вибачте, сталася помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_additional_services_keyboard(city, context)
        )
        return CHOOSING_ADDITIONAL_SERVICES

async def district_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору району"""
    try:
        district = update.message.text
        city = context.user_data.get('selected_city')
        
        if district == BACK_BUTTON:
            # Видаляємо останній вибір району
            remove_choice_by_type(context, 'Район')
            # Повертаємось до вибору району
            await update.message.reply_text(
                "Оберіть додаткові послуги:",
                reply_markup=create_additional_services_keyboard(city, context)
            )
            return CHOOSING_ADDITIONAL_SERVICES
            
        # Перевіряємо чи існує такий район у конфігурації
        if district not in TAXI_PRICES[city]:
            await update.message.reply_text(
                "Будь ласка, оберіть район зі списку:",
                reply_markup=create_district_keyboard(city)
            )
            return CHOOSING_DISTRICT
        
        # Зберігаємо вибір району
        add_choice(context, "Район", district)
        
        # Отримуємо вартість таксі
        taxi_price = TAXI_PRICES[city][district]
        price_text = f"{taxi_price} грн" if isinstance(taxi_price, (int, float)) else taxi_price
        
        # Відправляємо повідомлення про вибір району
        await update.message.reply_text(
            f"🏘 Ви обрали район: {district}\n"
            f"🚕 Приблизна вартість таксі в один бік: {price_text}\n"
            "Вартість таксі може змінюватись!"
        )
        
        # Переходимо до підсумкового меню
        await show_summary(update, context)
        return CHOOSING_SUMMARY
        
    except Exception as e:
        logger.error(f"[DISTRICT] Помилка при обробці вибору району: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_district_keyboard(city)
        )
        return CHOOSING_DISTRICT

async def show_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показує підсумок вибору користувача"""
    try:
        # Debug: Log user data for troubleshooting
        logger.info(f"[SUMMARY] context.user_data at start: {context.user_data}")
        
        # Отримуємо всі вибори користувача
        choices = context.user_data.get('choices', [])
        
        # Формуємо базову інформацію
        summary = "📋 Приблизний прорахунок свята:\n\n"
        
        # Додаємо основну інформацію
        for choice in choices:
            if choice['type'] in ["Місто", "Тип події", "Локація", "Тематика", "Підтема", "Формат"]:
                summary += f"{choice['type']}: {choice['value']}\n"
        
        # Додаємо деталі вартості
        summary += "\n💰 Деталі вартості:\n"
        
        # Додаємо на початку функції (після отримання choices):
        city = context.user_data.get('selected_city')
        if not city:
            city = next((choice['value'] for choice in choices 
                        if choice['type'] == "Місто"), None)
        
        # Підраховуємо загальну вартість
        total_price = 0
        
        # Додаємо ціну пакету
        for choice in choices:
            if choice['type'] == "Пакет":
                city = next((c['value'] for c in choices if c['type'] == "Місто"), None)
                event_type = next((e['value'] for e in choices if e['type'] == "Тип події"), None)
                logger.info(f"[SUMMARY] Знайдено пакет: {choice['value']} для міста {city} та типу події {event_type}")
                if city and event_type and city in PAKET_PRICES and event_type in PAKET_PRICES[city]:
                    logger.info(f"[SUMMARY] PAKET_PRICES для міста {city} та типу події {event_type}: {PAKET_PRICES[city][event_type]}")
                    if choice['value'] in PAKET_PRICES[city][event_type]:
                        package_price = PAKET_PRICES[city][event_type][choice['value']]
                        total_price += package_price
                        summary += f"Пакет: {choice['value']} - {package_price} грн\n"
            elif choice['type'] == "Квест":
                import re
                city = next((c['value'] for c in choices if c['type'] == "Місто"), None)
                
                try:
                    match = re.match(r"(.+?\(.*?\))\s*\((.*?)\)$", choice['value'])
                    if match:
                        quest_name = match.group(1).strip()
                        duration = match.group(2).strip()
                        price = QWEST[city][quest_name][duration]
                        total_price += price
                        summary += f"Квест: {quest_name} ({duration}) - {price} грн\n"
                    else:
                        logger.error(f"[SUMMARY] Не вдалося розпарсити квест: {choice['value']}")
                        summary += f"Квест: {choice['value']}: Ціна уточнюється\n"
                except Exception as e:
                    logger.error(f"[SUMMARY] Помилка при обробці ціни квесту: {str(e)}")
                    summary += f"Квест: {choice['value']}: Ціна уточнюється\n"
            elif choice['type'] == 'Погодинна ціна':
                # Витягуємо ціну з тексту
                price_text = choice['value']
                if "грн" in price_text:
                    price = int(price_text.split("грн")[0].strip().split()[-1])
                    total_price += price
                    summary += f"Погодинна оплата: {price_text}\n"
                else:
                    summary += f"Погодинна оплата: {price_text}\n"
        
        # Додаємо ціни за додаткові послуги
        if 'additional_services' in context.user_data:
            for service, option in context.user_data['additional_services'].items():
                try:
                    # Підтримка формату: просто число з "грн" (наприклад, "4000 грн")
                    if isinstance(option, str) and option.strip().endswith('грн') and option.strip().replace(' грн', '').replace(' ', '').isdigit():
                        price = int(option.strip().split()[0])
                        total_price += price
                        summary += f"➕ {service}: {option}\n"
                    elif ' - ' in option:
                        # Для шоу та інших послуг з форматом "НАЗВА - ЦІНА"
                        price_str = option.split(' - ')[1]
                        if 'грн' in price_str:
                            try:
                                price = int(price_str.split()[0])
                                total_price += price
                                summary += f"➕ {service}: {option}\n"
                            except ValueError:
                                summary += f"➕ {service}: {option}\n"
                        else:
                            summary += f"➕ {service}: {option}\n"
                    else:
                        # Для майстер-класів та інших послуг з форматом "НАЗВА - ДЕТАЛІ - ЦІНА"
                        try:
                            # Розбиваємо рядок на частини
                            parts = option.split(' - ')
                            if len(parts) >= 2:
                                # Беремо останню частину як ціну
                                price_str = parts[-1]
                                if 'грн' in price_str:
                                    price = int(price_str.split()[0])
                                    total_price += price
                            summary += f"➕ {service}: {option}\n"
                        except Exception as e:
                            logger.error(f"[SUMMARY] Помилка при обробці ціни для {service}: {str(e)}")
                            summary += f"➕ {service}: {option}\n"
                except Exception as e:
                    logger.error(f"[SUMMARY] Помилка при обробці ціни додаткової послуги: {str(e)}")
                    summary += f"➕ {service}: {option}\n"
        
        # Додаємо вартість таксі
        district = next((choice['value'] for choice in choices if choice['type'] == "Район"), None)
        if district and city:
            try:
                taxi_price = TAXI_PRICES[city][district]
                if isinstance(taxi_price, (int, float)):
                    total_price += taxi_price
                    summary += f"🚕 Таксі ({district}): {taxi_price} грн\n"
                else:
                    summary += f"🚕 Таксі ({district}): {taxi_price}\n"
            except Exception as e:
                logger.error(f"[SUMMARY] Помилка при обробці ціни таксі: {str(e)}")
                summary += f"🚕 Таксі ({district}): Ціна уточнюється\n"
        
        # Додаємо загальну вартість
        summary += f"\n💵 Приблизна загальна вартість: {total_price} грн\n"
        
        # Додаємо попередження про зміну цін
        summary += "\n⚠️ Зверніть увагу: це приблизний розрахунок, фінальна вартість може змінюватись"
        
        # Відправляємо повідомлення
        await update.message.reply_text(
            summary,
            reply_markup=create_summary_keyboard()
        )
        
    except Exception as e:
        logger.error(f"[SUMMARY] Помилка при формуванні підсумку: {str(e)} | context.user_data: {context.user_data}")
        await update.message.reply_text(
            "❌ Вибачте, сталася помилка при формуванні підсумку. Спробуйте ще раз.",
            reply_markup=create_summary_keyboard()
        )

async def summary_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка вибору в підсумковому меню"""
    try:
        text = update.message.text
        city = context.user_data.get('selected_city')
        if not city:
            city = next((choice['value'] for choice in context.user_data.get('choices', []) if choice['type'] == "Місто"), None)
        
        if text == BACK_BUTTON:
            # Видаляємо останній вибір району
            remove_choice_by_type(context, 'Район')
            
            # Повертаємось до вибору району
            await update.message.reply_text(
                "Оберіть ваш район:",
                reply_markup=create_district_keyboard(city)
            )
            return CHOOSING_DISTRICT
            
        elif text == "📅 Дізнатись час/дату":
            # 1. Надіслати підсумок менеджеру
            await send_summary_to_manager(update, context)
            # 2. Показати користувачу повідомлення про успішне надсилання
            await update.message.reply_text(
                "Ваше замовлення надіслано менеджеру! Очікуйте дзвінка або повідомлення. Якщо бажаєте, можете залишити свій номер телефону для зв'язку:",
                reply_markup=ReplyKeyboardMarkup([
                    [KeyboardButton('📱 Надіслати номер телефону', request_contact=True)],
                    [KeyboardButton('⬅️ На початок')]
                ], resize_keyboard=True)
            )
            return PHONE_CONTACT
            
        else:
            await update.message.reply_text(
                "Будь ласка, використовуйте кнопки для вибору опції.",
                reply_markup=create_summary_keyboard()
            )
            return CHOOSING_SUMMARY
            
    except Exception as e:
        logger.error(f"[SUMMARY] Помилка при обробці вибору в підсумковому меню: {str(e)}")
        await update.message.reply_text(
            "Виникла помилка. Будь ласка, спробуйте ще раз.",
            reply_markup=create_summary_keyboard()
        )
        return CHOOSING_SUMMARY

async def summary_chosen_contact_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробка наданих контактів в підсумковому меню"""
    try:
        logger.info(f"[SUMMARY_CONTACT] update.message: {update.message}")
        logger.info(f"[SUMMARY_CONTACT] context.user_data: {context.user_data}")
        # Якщо натиснуто "На початок"
        if update.message.text == "⬅️ На початок":
            logger.info("[SUMMARY_CONTACT] Натиснуто 'На початок'. Очищаю context.user_data.")
            context.user_data.clear()
            await update.message.reply_text(
                Hello_World,
                reply_markup=create_city_keyboard()
            )
            return CHOOSING_CITY

        # Якщо користувач надіслав контакт
        if update.message.contact:
            logger.info(f"[SUMMARY_CONTACT] Надіслано контакт: {update.message.contact}")
            phone = update.message.contact.phone_number
            user = update.effective_user
            contact_info = (
                f"<b>Контакт від користувача</b>\n"
                f"ID: <code>{user.id}</code>\n"
                f"Ім'я: {user.first_name or ''} {user.last_name or ''}\n"
                f"Username: @{user.username if user.username else '-'}\n"
                f"Телефон: <code>{phone}</code>"
            )
            await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=contact_info, parse_mode='HTML')
            await update.message.reply_text(
                "Дякуємо! Ваш контакт передано менеджеру. Очікуйте найближчим часом з вами зв'яжуться для уточнення.",
                reply_markup=create_city_keyboard()
            )
            # --- ЗБЕРЕЖЕННЯ КОНТАКТУ В БАЗІ ДАНИХ ---
            user_info = get_unified_user_info(user, user_data.get_user(user.id), update)
            user_info['phone_number'] = phone
            user_data.add_user(user.id, user_info)
            logger.info(f"[SUMMARY_CONTACT] Контакт збережено для user_id={user.id}")
            context.user_data.clear()
            return CHOOSING_CITY
        
        # Якщо користувач надіслав щось інше
        await update.message.reply_text(
            "Будь ласка, надішліть номер телефону або натисніть '⬅️ На початок'.",
            reply_markup=create_summary_keyboard()
        )
        return CHOOSING_SUMMARY

    except Exception as e:
        logger.error(f"[SUMMARY_CONTACT] Помилка при обробці наданих контактів в підсумковому меню: {str(e)}")
        logger.exception(e)
        await update.message.reply_text(
            "Вибачте, сталася помилка. Спробуйте ще раз або зверніться до менеджера.",
            reply_markup=create_summary_keyboard()
        )
        return CHOOSING_SUMMARY

# ============================================
# СИСТЕМНІ ФУНКЦІЇ
# ============================================
async def save_state(update: Update, context: ContextTypes.DEFAULT_TYPE, state: int) -> None:
    """Зберігає поточний стан розмови"""
    if user_data and update.effective_user:
        # Уніфікований запис стану у вкладеному полі 'state'
        state_inner = {
            'choices': context.user_data.get('choices', []),
            'last_state': state,
            'last_update': datetime.now().isoformat()
        }
        user_data.save_conversation_state(update.effective_user.id, {'state': state_inner})

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасування розмови"""
    if user_data and update.effective_user:
        user_data.clear_conversation_state(update.effective_user.id)
    
    await update.message.reply_text(
        'Виникла помилка. Щоб почати спочатку, використайте команду /start'
    )
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє всі текстові повідомлення"""
    # Перевіряємо, чи є збережений стан
    if not context.user_data.get('choices'):
        # Якщо немає збереженого стану, показуємо меню вибору міст
        await update.message.reply_text(
            Hello_World,
            reply_markup=create_city_keyboard()
        )
        return CHOOSING_CITY
    
    # Отримуємо останній стан
    last_choice = context.user_data['choices'][-1]
    
    # Відновлюємо відповідний стан на основі останнього вибору
    if last_choice['type'] == "Місто":
        await update.message.reply_text(
            "Оберіть яку подію будете святкувати:",
            reply_markup=create_event_type_keyboard()
        )
        return CHOOSING_EVENT_TYPE
    elif last_choice['type'] == "Тип події":
        await update.message.reply_text(
            "Оберіть місце де хотіли б святкувати:",
            reply_markup=create_location_keyboard(last_choice['value'])
        )
        return CHOOSING_LOCATION
    elif last_choice['type'] == "Формат":
        await update.message.reply_text(
            "Оберіть тематику свята:",
            reply_markup=create_theme_keyboard()
        )
        return CHOOSING_THEME
    else:
        # Якщо не вдалося визначити стан, починаємо з початку
        await update.message.reply_text(
            Hello_World,
            reply_markup=create_city_keyboard()
        )
        return CHOOSING_CITY

# ============================================
# БЛОК МЕНЕДЖЕРА
# ============================================
async def export_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Відправка менеджеру файлу з усіма користувачами у правильному форматі"""
    user_id = update.effective_user.id
    if MANAGER_CHAT_ID is None or user_id != MANAGER_CHAT_ID:
        await update.message.reply_text("⛔ Доступ заборонено")
        return
    data = []
    for uid, info in user_data.users.items():
        try:
            numeric_uid = int(uid)
        except (ValueError, TypeError):
            continue
        row = {
            'user_id': info.get('user_id', ''),
            'username': info.get('username', ''),
            'first_name': info.get('first_name', ''),
            'last_name': info.get('last_name', ''),
            'language_code': info.get('language_code', ''),
            'is_bot': info.get('is_bot', ''),
            'status': (info or {}).get('status', ''),
            'last_update': info.get('last_update', ''),
            'created_at': (info or {}).get('created_at', ''),
            'phone_number': info.get('phone_number', ''),
            'chat_id': info.get('chat_id', ''),
            'type': info.get('type', ''),
            'city': info.get('city', ''),
            'order_count': info.get('order_count', 0),
            'visits': info.get('visits', 0),
            'device_info': info.get('device_info', ''),
        }
        data.append(row)
    # Формуємо DataFrame з потрібним порядком колонок
    columns = [
        'user_id', 'username', 'first_name', 'last_name', 'language_code', 'phone_number',
        'is_bot', 'status', 'last_update', 'created_at', 'chat_id', 'type', 'city', 'order_count', 'visits', 'device_info'
    ]
    df = pd.DataFrame(data, columns=columns)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    await context.bot.send_document(
        chat_id=MANAGER_CHAT_ID,
        document=buffer,
        filename="users.xlsx",
        caption="📋 Список всіх користувачів"
    )

# --- Менеджерські функції ---
from telegram.constants import ChatAction

async def broadcast_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Розсилка повідомлення/файлу всім користувачам (тільки для менеджера)"""
    user_id = update.effective_user.id
    if MANAGER_CHAT_ID is None or user_id != MANAGER_CHAT_ID:
        await update.message.reply_text("⛔ Доступ заборонено")
        return
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text("Введіть текст або зробіть reply до повідомлення з файлом/медіа!")
        return
    msg_text = ' '.join(context.args)
    media_msg = update.message.reply_to_message
    sent, failed = 0, 0
    for uid, info in user_data.users.items():
        chat_id = info.get('chat_id')
        if not chat_id:
            continue
        try:
            # Відправляємо текст
            if msg_text.strip():
                await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode='HTML')
            # Відправляємо медіа з replied повідомлення
            if media_msg:
                if media_msg.photo:
                    await context.bot.send_photo(chat_id=chat_id, photo=media_msg.photo[-1].file_id, caption=msg_text or None)
                if media_msg.document:
                    await context.bot.send_document(chat_id=chat_id, document=media_msg.document.file_id, caption=msg_text or None)
                if media_msg.video:
                    await context.bot.send_video(chat_id=chat_id, video=media_msg.video.file_id, caption=msg_text or None)
                if media_msg.audio:
                    await context.bot.send_audio(chat_id=chat_id, audio=media_msg.audio.file_id, caption=msg_text or None)
            sent += 1
        except Exception as e:
            failed += 1
    await update.message.reply_text(f'✅ Розіслано: {sent}\n❌ Не вдалося: {failed}')

async def hello_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Звернення до конкретного користувача: /hello ID повідомлення (тільки для менеджера)"""
    user_id = update.effective_user.id
    if MANAGER_CHAT_ID is None or user_id != MANAGER_CHAT_ID:
        await update.message.reply_text("⛔ Доступ заборонено")
        return
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Використання: /hello ID повідомлення")
        return
    target_id = context.args[0]
    try:
        target_id = int(target_id)
    except ValueError:
        await update.message.reply_text("ID повинен бути числом!")
        return
    msg_text = ' '.join(context.args[1:])
    try:
        await context.bot.send_message(chat_id=target_id, text=msg_text)
        await update.message.reply_text("✅ Надіслано!")
    except Exception as e:
        await update.message.reply_text(f"❌ Не вдалося: {e}")

# --- Надсилання підсумку менеджеру ---
async def send_summary_to_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Формує і надсилає менеджеру всі деталі користувача та замовлення"""
    user = update.effective_user
    logger.info(f"[SEND_SUMMARY] Виклик send_summary_to_manager для user_id={user.id}")
    logger.info(f"[SEND_SUMMARY] context.user_data: {context.user_data}")
    choices = context.user_data.get('choices', [])
    additional_services = context.user_data.get('additional_services', {})
    summary_lines = [
        f"<b>Нове звернення від користувача</b>",
        f"ID: <code>{user.id}</code>",
        f"Ім'я: {user.full_name}\n",
        f"Username: @{user.username if user.username else '-'}",
        f"Мова: {user.language_code or '-'}",
        f"\n<b>Вибір користувача:</b>"
    ]
    for ch in choices:
        summary_lines.append(f"• <b>{ch['type']}</b>: {ch['value']}")
    if additional_services:
        summary_lines.append("\n<b>Додаткові послуги:</b>")
        for service, option in additional_services.items():
            summary_lines.append(f"➕ {service}: {option}")
    summary = '\n'.join(summary_lines)
    logger.info(f"[SEND_SUMMARY] summary to send: {summary}")
    logger.info(f"[SEND_SUMMARY] MANAGER_CHAT_ID: {MANAGER_CHAT_ID}")
    try:
        await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=summary, parse_mode='HTML')
        logger.info("[SEND_SUMMARY] Повідомлення менеджеру успішно надіслано!")
    except Exception as e:
        logger.error(f"Не вдалося надіслати підсумок менеджеру: {e}")

        
# ============================================
# ОСНОВНА ФУНКЦІЯ
# ============================================

def main():
    """Запуск бота"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Налаштування обробника розмови
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_chosen)],
            CHOOSING_EVENT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_type_chosen)],
            CHOOSING_EVENT_TYPE_Sim_svjata: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_type_chosen__Sim_svjata)],
            FFMILY_DOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_dop_chosen)],
            CHOOSING_EVENT_TYPE_inshe: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_type_chosen_inshe)],
            CHOOSING_EVENT_TYPE_afisha: [MessageHandler(filters.TEXT & ~filters.COMMAND, event_type_chosen_afisha)],
            CHOOSING_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_chosen)],
            CHOOSING_LOCATION_inshe: [MessageHandler(filters.TEXT & ~filters.COMMAND, location_chosen_inshe)],
            CHOOSING_THEME: [MessageHandler(filters.TEXT & ~filters.COMMAND, theme_chosen)],
            CHOOSING_THEME2: [MessageHandler(filters.TEXT & ~filters.COMMAND, theme2_chosen)],
            CHOOSING_THEME_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, theme_details_chosen)],
            CHOOSING_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, format_chosen)],
            CHOOSING_HOURLY_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hourly_price_chosen)],
            CHOOSING_PACKAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, package_chosen)],
            CHOOSING_QWEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, qwest_chosen)],
            CHOOSING_QWEST_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, qwest_duration_chosen)],
            CHOOSING_FINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_chosen)],
            CHOOSING_ADDITIONAL_SERVICES: [MessageHandler(filters.TEXT & ~filters.COMMAND, additional_services_chosen)],
            CHOOSING_SERVICE_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, additional_services_chosen)],
            CHOOSING_DISTRICT: [MessageHandler(filters.TEXT & ~filters.COMMAND, district_chosen)],
            CHOOSING_SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary_chosen)],
            PHONE_CONTACT: [
                MessageHandler(filters.CONTACT, summary_chosen_contact_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, summary_chosen_contact_phone),
            ],
            
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start)],
    )
    
    application.add_handler(conv_handler)
    # Додаємо глобальні обробники для /start та /reset
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('users', export_users_command))
    application.add_handler(CommandHandler('all', broadcast_all_command))
    application.add_handler(CommandHandler('hello', hello_user_command))
    application.run_polling()

if __name__ == '__main__':
    main()
