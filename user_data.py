import json
import os
from typing import Dict, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
import certifi

class UserData:
    def __init__(self):
        self.users: Dict[str, dict] = {}
        self.filename = "users.json"
        
        # Підключення до MongoDB
        mongodb_url = os.environ.get('MONGODB_URI')
        if mongodb_url:
            try:
                print("Спроба підключення до MongoDB...")
                # Використовуємо стандартні налаштування для Atlas
                self.client = MongoClient(
                    mongodb_url,
                    retryWrites=True,
                    w='majority',
                    tlsCAFile=certifi.where()
                )
                
                # Перевіряємо підключення
                print("Перевірка з'єднання...")
                self.client.admin.command('ping')
                
                self.db = self.client.get_database('confetti')
                self.users_collection = self.db.get_collection('users')
                print("Успішно підключено до MongoDB")
            except Exception as e:
                print(f"Помилка підключення до MongoDB: {str(e)}")
                print("Використовую локальне сховище")
                self.client = None
                self.users_collection = None
        else:
            print("MONGODB_URI не знайдено, використовую локальне сховище")
            self.client = None
            self.users_collection = None
            
        self.load_data()

    def load_data(self):
        """Завантаження даних з MongoDB або локального файлу"""
        if self.users_collection is not None:
            try:
                # Завантаження з MongoDB
                cursor = self.users_collection.find({})
                self.users = {str(doc['_id']): {k: v for k, v in doc.items() if k != '_id'} 
                            for doc in cursor}
            except Exception as e:
                print(f"Помилка завантаження даних з MongoDB: {e}")
                self.users = {}
        else:
            # Завантаження з локального файлу
            if os.path.exists(self.filename):
                try:
                    with open(self.filename, 'r', encoding='utf-8') as file:
                        self.users = json.load(file)
                except json.JSONDecodeError:
                    self.users = {}

    def save_data(self):
        """Збереження даних в MongoDB або локальний файл"""
        if self.users_collection is not None:
            try:
                # Зберігання в MongoDB
                for user_id, user_data in self.users.items():
                    self.users_collection.update_one(
                        {'_id': user_id},
                        {'$set': user_data},
                        upsert=True
                    )
            except Exception as e:
                print(f"Помилка збереження даних в MongoDB: {e}")
                # Якщо помилка - зберігаємо локально
                with open(self.filename, 'w', encoding='utf-8') as file:
                    json.dump(self.users, file, ensure_ascii=False, indent=2)
        else:
            # Зберігання в локальний файл
            with open(self.filename, 'w', encoding='utf-8') as file:
                json.dump(self.users, file, ensure_ascii=False, indent=2)

    def add_user(self, user_id: str, user_data: dict):
        """Додавання нового користувача"""
        self.users[str(user_id)] = user_data
        self.save_data()

    def get_user(self, user_id: str) -> Optional[dict]:
        """Отримання даних користувача"""
        return self.users.get(str(user_id))

    def get_all_users(self) -> Dict[str, dict]:
        """Отримання всіх користувачів"""
        return self.users

    def update_user(self, user_id: str, user_data: dict):
        """Оновлення даних користувача"""
        if str(user_id) in self.users:
            self.users[str(user_id)].update(user_data)
            self.save_data()

    def delete_user(self, user_id: str):
        """Видалення користувача"""
        if str(user_id) in self.users:
            del self.users[str(user_id)]
            if self.users_collection is not None:
                try:
                    self.users_collection.delete_one({'_id': str(user_id)})
                except Exception as e:
                    print(f"Помилка видалення користувача з MongoDB: {e}")
            self.save_data()

# Створюємо глобальний екземпляр
user_data = UserData() 
