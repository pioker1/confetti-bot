import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

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
            self.client = MongoClient(self.mongo_uri)
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

# Створення глобального екземпляру
try:
    user_data = UserData()
except Exception as e:
    logger.error(f"Не вдалося створити екземпляр UserData: {e}")
    user_data = None 
