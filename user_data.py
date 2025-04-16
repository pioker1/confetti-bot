import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv
from telegram import Contact

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Завантаження змінних середовища
load_dotenv()

class UserData:
    def __init__(self):
        self.mongo_uri = os.getenv('MONGODB_URI')
        if not self.mongo_uri:
            logger.error("Не знайдено URI MongoDB в змінних середовища")
            raise ValueError("Не знайдено URI MongoDB")
        
        try:
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            # Перевіряємо підключення
            self.client.admin.command('ping')
            self.db = self.client.get_database()
            self.collection = self.db.users
            logger.info("Успішно підключено до MongoDB")
        except Exception as e:
            logger.error(f"Помилка підключення до MongoDB: {e}")
            raise

    def add_user(self, user_id: int, user_data: dict):
        try:
            self.collection.update_one(
                {'user_id': user_id},
                {'$set': user_data},
                upsert=True
            )
            logger.info(f"Додано/оновлено дані користувача {user_id}")
        except Exception as e:
            logger.error(f"Помилка при додаванні користувача {user_id}: {e}")
            raise

    def get_user(self, user_id: int) -> dict:
        try:
            user = self.collection.find_one({'user_id': user_id})
            return user if user else {}
        except Exception as e:
            logger.error(f"Помилка при отриманні даних користувача {user_id}: {e}")
            return {}

    def update_user(self, user_id: int, update_data: dict):
        try:
            self.collection.update_one(
                {'user_id': user_id},
                {'$set': update_data}
            )
            logger.info(f"Оновлено дані користувача {user_id}")
        except Exception as e:
            logger.error(f"Помилка при оновленні даних користувача {user_id}: {e}")
            raise

    def delete_user(self, user_id: int):
        try:
            self.collection.delete_one({'user_id': user_id})
            logger.info(f"Видалено користувача {user_id}")
        except Exception as e:
            logger.error(f"Помилка при видаленні користувача {user_id}: {e}")
            raise

    def save_contact(self, user_id: int, contact: Contact):
        """Зберігає контактну інформацію користувача"""
        try:
            contact_data = {
                'phone_number': contact.phone_number,
                'first_name': contact.first_name,
                'last_name': contact.last_name if contact.last_name else None,
                'user_id': contact.user_id if contact.user_id else None
            }
            
            self.collection.update_one(
                {'user_id': user_id},
                {'$set': {'contact': contact_data}},
                upsert=True
            )
            logger.info(f"Збережено контакт користувача {user_id}")
        except Exception as e:
            logger.error(f"Помилка при збереженні контакту користувача {user_id}: {e}")
            raise

    def get_contact(self, user_id: int) -> dict:
        """Отримує контактну інформацію користувача"""
        try:
            user = self.collection.find_one({'user_id': user_id})
            return user.get('contact', {}) if user else {}
        except Exception as e:
            logger.error(f"Помилка при отриманні контакту користувача {user_id}: {e}")
            return {}

# Створення глобального екземпляру з повторними спробами
max_retries = 3
retry_count = 0
user_data = None

while retry_count < max_retries and user_data is None:
    try:
        user_data = UserData()
        logger.info("Успішно створено екземпляр UserData")
    except Exception as e:
        retry_count += 1
        logger.error(f"Спроба {retry_count} з {max_retries} невдала: {e}")
        if retry_count == max_retries:
            logger.error("Досягнуто максимальну кількість спроб підключення до MongoDB") 
