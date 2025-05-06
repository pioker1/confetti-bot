import os
import json
import logging
from typing import Dict, Optional, Any, Union
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError
from datetime import datetime
import certifi

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class UserData:
    def __init__(self, mongo_uri: Optional[str] = None):
        self.users: Dict[str, dict] = {}
        self.filename = "users.json"
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.users_collection: Optional[Collection] = None
        self.conversations: Optional[Collection] = None
        
        # Спробуємо підключитися до MongoDB
        if mongo_uri:
            try:
                logger.info("Спроба підключення до MongoDB...")
                self.client = MongoClient(
                    mongo_uri,
                    tlsCAFile=certifi.where(),
                    serverSelectionTimeoutMS=10000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000,
                    maxPoolSize=1,
                    waitQueueTimeoutMS=10000,
                    retryWrites=True,
                    w='majority'
                )
                
                # Перевіряємо підключення
                self.client.admin.command('ping')
                
                # Отримуємо базу даних
                self.db = self.client.get_database('confetti')
                self.users_collection = self.db.users
                self.conversations = self.db.conversations
                
                # Створюємо індекси
                self._create_indexes()
                
                logger.info("Успішно підключено до MongoDB")
            except Exception as e:
                logger.error(f"Помилка підключення до MongoDB: {str(e)}")
                logger.info("Використовую локальне сховище")
                self.client = None
                self.users_collection = None
                self.conversations = None
        else:
            logger.info("MONGODB_URI не знайдено, використовую локальне сховище")
            
        # Завантажуємо дані
        self.load_data()

    def _create_indexes(self):
        """Створення індексів для колекцій"""
        try:
            # Індекси для користувачів
            self.users_collection.create_index(
                [('user_id', 1)],
                unique=True,
                partialFilterExpression={'user_id': {'$type': 'number'}}
            )
            
            # Індекси для розмов
            self.conversations.create_index(
                [('user_id', 1)],
                unique=True,
                partialFilterExpression={'user_id': {'$type': 'number'}}
            )
            logger.info("Індекси успішно створено")
        except Exception as e:
            logger.error(f"Помилка створення індексів: {str(e)}")

    def load_data(self):
        """Завантаження даних з MongoDB або локального файлу"""
        if self.users_collection is not None:
            try:
                cursor = self.users_collection.find({})
                self.users = {str(doc['_id']): {k: v for k, v in doc.items() if k != '_id'} 
                            for doc in cursor}
                logger.info("Дані успішно завантажено з MongoDB")
            except Exception as e:
                logger.error(f"Помилка завантаження даних з MongoDB: {e}")
                self.users = {}
        else:
            if os.path.exists(self.filename):
                try:
                    with open(self.filename, 'r', encoding='utf-8') as file:
                        self.users = json.load(file)
                    logger.info("Дані успішно завантажено з локального файлу")
                except json.JSONDecodeError:
                    logger.error("Помилка читання локального файлу")
                    self.users = {}

    def save_data(self):
        """Збереження даних в MongoDB або локальний файл"""
        if self.users_collection is not None:
            try:
                for user_id, user_data in self.users.items():
                    self.users_collection.update_one(
                        {'_id': user_id},
                        {'$set': user_data},
                        upsert=True
                    )
                logger.info("Дані успішно збережено в MongoDB")
            except Exception as e:
                logger.error(f"Помилка збереження в MongoDB: {e}")
                self._save_local()
        else:
            self._save_local()

    def _save_local(self):
        """Збереження даних в локальний файл"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as file:
                json.dump(self.users, file, ensure_ascii=False, indent=2)
            logger.info("Дані успішно збережено локально")
        except Exception as e:
            logger.error(f"Помилка збереження локально: {e}")

    def ensure_connected(self) -> bool:
        """Перевірка підключення до MongoDB"""
        if not self.client:
            return False
            
        try:
            self.client.server_info()
            return True
        except:
            return False

    def save_conversation_state(self, user_id: int, state: Dict[str, Any]) -> bool:
        """Зберігає стан розмови користувача"""
        if self.conversations is not None and self.ensure_connected():
            try:
                # Встановлюємо правильний user_id (int) для збереження
                state['user_id'] = int(user_id)
                # Оновлюємо last_update для експорту
                state['last_update'] = datetime.now().isoformat()
                self.conversations.update_one(
                    {'user_id': int(user_id)},
                    {'$set': state},
                    upsert=True
                )
                logger.info(f"Збережено стан розмови для користувача {user_id}")
                return True
            except Exception as e:
                logger.error(f"Помилка збереження стану розмови: {str(e)}")
        return False

    def get_conversation_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Отримує стан розмови користувача"""
        if self.conversations is not None and self.ensure_connected():
            try:
                # user_id має бути int
                state = self.conversations.find_one({'user_id': int(user_id)})
                if state:
                    state.pop('_id', None)
                return state
            except Exception as e:
                logger.error(f"Помилка отримання стану розмови: {str(e)}")
        return None

    def clear_conversation_state(self, user_id: Union[str, int]) -> None:
        """Очищає стан розмови для конкретного користувача"""
        user_id = str(user_id)
        try:
            if self.conversations is not None and self.ensure_connected():
                self.conversations.update_one(
                    {'user_id': user_id},
                    {'$set': {'state': {}, 'last_updated': datetime.now()}},
                    upsert=True
                )
            else:
                if not os.path.exists(self.filename):
                    with open(self.filename, 'w') as f:
                        json.dump({}, f)
                
                with open(self.filename, 'r') as f:
                    conversations = json.load(f)
                
                conversations[user_id] = {
                    'state': {},
                    'last_updated': datetime.now().isoformat()
                }
                
                with open(self.filename, 'w') as f:
                    json.dump(conversations, f)
                
        except Exception as e:
            logger.error(f"Помилка при очищенні стану розмови для користувача {user_id}: {e}")
            # Якщо виникла помилка, створюємо пустий стан в пам'яті
            self.users[user_id] = {}

    def add_user(self, user_id: int, user_info: dict) -> bool:
        """Додає нового користувача або оновлює існуючого, не затираючи старі дані та синхронізуючи _id/user_id"""
        try:
            str_id = str(user_id)
            # Оновлюємо лише ті поля, що є у user_info, інші залишаємо
            old_info = self.users.get(str_id, {}).copy()
            old_info.update(user_info)
            # Не перезаписуємо created_at, якщо він вже існує
            old_info['created_at'] = old_info.get('created_at', datetime.now().isoformat())
            # Синхронізуємо _id та user_id для MongoDB
            old_info['_id'] = str_id
            old_info['user_id'] = int(user_id)
            self.users[str_id] = old_info

            if self.users_collection is not None and self.ensure_connected():
                self.users_collection.update_one(
                    {'_id': str_id},
                    {'$set': old_info},
                    upsert=True
                )
            else:
                self.save_data()

            logger.info(f"Додано/оновлено користувача: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Помилка додавання користувача: {str(e)}")
            return False

    def get_user(self, user_id: int) -> Optional[dict]:
        """Отримує інформацію про користувача"""
        try:
            str_id = str(user_id)
            if self.users_collection is not None and self.ensure_connected():
                user = self.users_collection.find_one({'_id': str_id})
                if user:
                    return {k: v for k, v in user.items() if k != '_id'}
            return self.users.get(str_id)
        except Exception as e:
            logger.error(f"Помилка отримання користувача: {str(e)}")
            return None

# Створення глобального екземпляра
mongo_uri = os.getenv('MONGODB_URI')
user_data = UserData(mongo_uri) 
