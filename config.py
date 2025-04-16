import os
import logging
from dotenv import load_dotenv

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Завантаження змінних середовища
load_dotenv()

# Telegram конфігурація
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Отримання та конвертація ID менеджера
try:
    MANAGER_CHAT_ID = int(os.getenv('MANAGER_CHAT_ID'))
    logger.info(f"ID менеджера успішно завантажено: {MANAGER_CHAT_ID}")
except (TypeError, ValueError) as e:
    logger.error(f"Помилка при завантаженні ID менеджера: {str(e)}")
    MANAGER_CHAT_ID = None

# Перевірка наявності необхідних змінних
if not TELEGRAM_BOT_TOKEN:
    logger.error("Не знайдено токен бота в змінних середовища")
if not MANAGER_CHAT_ID:
    logger.error("Не знайдено ID менеджера в змінних середовища")

# Налаштування кнопок меню
CITIES = ['Київ', 'Кривий Ріг']

EVENT_TYPES = [
    'День народження',
    'Випускний',
    'Сімейне свято',
    'Інше'
]

LOCATIONS = [
    'Додому',
    'В кафе',
    'Садочок-школа',
    'Турбаза',
    'Інше'
]

DURATIONS = {
    'Додому/кафе': ['1 година', '1.5 години', '2 години', '3 години', 'більше'],
    'Турбаза': ['2 години', '3 години', 'більше'],
    'Садочок-школа': ['1 година', '1.5 години', '2 години', '3 години', 'більше']
}

# Базові ціни за годину в залежності від локації
BASE_PRICES = {
    'Домой': 1000,
    'В кафе': 1000,
    'Садочок-школа': 1500,
    'Турбаза': 2000,
    'Інше': 1500
}

# Множник ціни в залежності від тривалості
DURATION_MULTIPLIERS = {
    '1 година': 1,
    '1.5 години': 1.5,
    '2 години': 2,
    '3 години': 3
}

# Ціни на додаткові послуги
ADDITIONAL_SERVICES = {
    'Шоу програма': {'name': 'Шоу програма', 'price': 1500},
    'Майстер класи': {'name': 'Майстер класи', 'price': 800},
    'Квести': {'name': 'Квести', 'price': 1000},
    'Піньята': {'name': 'Піньята', 'price': 500},
    'Білий ведмедик': {'name': 'Білий ведмедик', 'price': 700},
    'Експрес привітання': {'name': 'Експрес привітання', 'price': 300},
    'Бабл машина': {'name': 'Бабл машина', 'price': 400},
    'Святкування річниці': {'name': 'Святкування річниці', 'price': 1200},
    'Декор': {'name': 'Декор', 'price': 1000},
    'Фотограф': {'name': 'Фотограф', 'price': 1500},
    'Відеограф': {'name': 'Відеограф', 'price': 2000},
    'Діджей': {'name': 'Діджей', 'price': 1800}
}

# Контактна інформація менеджера
MANAGER_INFO = {
    'phone': '+380123456789',
    'telegram': 'https://t.me/manager_username',
    'name': 'Олена'
} 
