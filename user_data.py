import json
import os
from typing import Dict, Optional

class UserData:
    def __init__(self):
        self.users: Dict[str, dict] = {}
        self.filename = "users.json"
        self.load_data()

    def load_data(self):
        """Завантаження даних з файлу або з змінної оточення"""
        # Спочатку спробуємо завантажити з змінної оточення
        users_json = os.environ.get('USERS_DATA')
        if users_json:
            try:
                self.users = json.loads(users_json)
                return
            except json.JSONDecodeError:
                pass

        # Якщо немає в змінних оточення, спробуємо з файлу
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as file:
                    self.users = json.load(file)
            except json.JSONDecodeError:
                self.users = {}

    def save_data(self):
        """Збереження даних в файл та змінну оточення"""
        # Зберігаємо в файл для локальної розробки
        with open(self.filename, 'w', encoding='utf-8') as file:
            json.dump(self.users, file, ensure_ascii=False, indent=2)
        
        # Зберігаємо в змінну оточення для Heroku
        users_json = json.dumps(self.users, ensure_ascii=False)
        if 'HEROKU' in os.environ:
            os.environ['USERS_DATA'] = users_json

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
            self.save_data()

# Створюємо глобальний екземпляр
user_data = UserData() 
