import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv
from telegram import Contact
from urllib.parse import urlparse, urlunparse
from typing import Optional, Dict, Any
from datetime import datetime
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Завантаження змінних середовища
load_dotenv()

class UserData:
    def __init__(self, mongo_uri: str):
        if not mongo_uri:
            logger.error("Не знайдено URI MongoDB")
            raise ValueError("Не знайдено URI MongoDB")
            
        self.mongo_uri = mongo_uri
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.users: Optional[Collection] = None
        self.conversations: Optional[Collection] = None
        self.connect()

    def connect(self) -> bool:
        """Підключення до MongoDB"""
        try:
            # Встановлюємо з'єднання з обмеженням часу
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Перевіряємо з'єднання
            self.client.admin.command('ping')
            
            # Отримуємо базу даних
            self.db = self.client.get_database()
            self.users = self.db.users
            self.conversations = self.db.conversations
            
            # Створюємо індекси
            self.users.create_index('user_id', unique=True)
            self.conversations.create_index('user_id', unique=True)
            
            logger.info("Успішно підключено до MongoDB")
            return True
        except ServerSelectionTimeoutError as e:
            logger.error(f"Помилка підключення до MongoDB (таймаут): {str(e)}")
            return False
        except PyMongoError as e:
            logger.error(f"Помилка підключення до MongoDB: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Неочікувана помилка при підключенні до MongoDB: {str(e)}")
            return False

    def save_conversation_state(self, user_id: int, state: Dict[str, Any]) -> bool:
        """Зберігає стан розмови користувача"""
        try:
            state['updated_at'] = datetime.now()
            self.conversations.update_one(
                {'user_id': user_id},
                {'$set': state},
                upsert=True
            )
            logger.info(f"Збережено стан розмови для користувача {user_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Помилка збереження стану розмови: {str(e)}")
            return False

    def get_conversation_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Отримує стан розмови користувача"""
        try:
            state = self.conversations.find_one({'user_id': user_id})
            if state:
                state.pop('_id', None)  # Видаляємо _id з результату
            return state
        except PyMongoError as e:
            logger.error(f"Помилка отримання стану розмови: {str(e)}")
            return None

    def clear_conversation_state(self, user_id: int) -> bool:
        """Очищає стан розмови користувача"""
        try:
            self.conversations.delete_one({'user_id': user_id})
            logger.info(f"Очищено стан розмови для користувача {user_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Помилка очищення стану розмови: {str(e)}")
            return False

    def add_user(self, user_id: int, user_info: dict) -> bool:
        """Додає нового користувача"""
        try:
            user_info['created_at'] = datetime.now()
            self.users.update_one(
                {'user_id': user_id},
                {'$set': user_info},
                upsert=True
            )
            logger.info(f"Додано/оновлено користувача: {user_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Помилка додавання користувача: {str(e)}")
            return False

    def get_user(self, user_id: int) -> Optional[dict]:
        """Отримує інформацію про користувача"""
        try:
            user = self.users.find_one({'user_id': user_id})
            if user:
                user.pop('_id', None)  # Видаляємо _id з результату
            return user
        except PyMongoError as e:
            logger.error(f"Помилка отримання користувача: {str(e)}")
            return None

    def save_contact(self, user_id: int, contact: Contact):
        """Зберігає контактну інформацію користувача"""
        try:
            contact_data = {
                'phone_number': contact.phone_number,
                'first_name': contact.first_name,
                'last_name': contact.last_name if contact.last_name else None,
                'user_id': contact.user_id if contact.user_id else None
            }
            
            self.users.update_one(
                {'user_id': user_id},
                {'$set': {'contact': contact_data}},
                upsert=True
            )
            logger.info(f"Збережено контакт користувача {user_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Помилка при збереженні контакту користувача {user_id}: {e}")
            return False

    def get_contact(self, user_id: int) -> dict:
        """Отримує контактну інформацію користувача"""
        try:
            user = self.users.find_one({'user_id': user_id})
            return user.get('contact', {}) if user else {}
        except PyMongoError as e:
            logger.error(f"Помилка при отриманні контакту користувача {user_id}: {e}")
            return {}

# Створення глобального екземпляру з повторними спробами
max_retries = 3
retry_count = 0
user_data = None

while retry_count < max_retries and user_data is None:
    try:
        mongo_uri = os.getenv('MONGODB_URI')
        if not mongo_uri:
            logger.error("Не знайдено URI MongoDB в змінних середовища")
            break
            
        user_data = UserData(mongo_uri)
        logger.info("Успішно створено екземпляр UserData")
    except Exception as e:
        retry_count += 1
        logger.error(f"Спроба {retry_count} з {max_retries} невдала: {e}")
        if retry_count == max_retries:
            logger.error("Досягнуто максимальну кількість спроб підключення до MongoDB") 
