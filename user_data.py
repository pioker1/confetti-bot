import json
import os
from typing import Dict, List, Optional

class UserData:
    def __init__(self, filename: str = 'users.json'):
        self.filename = filename
        self.users: Dict[int, Dict] = {}
        self.load_data()

    def load_data(self):
        """Завантаження даних користувачів з файлу"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except Exception as e:
                print(f"Помилка при завантаженні даних: {e}")
                self.users = {}

    def save_data(self):
        """Збереження даних користувачів у файл"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Помилка при збереженні даних: {e}")

    def add_user(self, user_id: int, user_data: Dict):
        """Додавання нового користувача"""
        self.users[str(user_id)] = user_data
        self.save_data()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Отримання даних користувача"""
        return self.users.get(str(user_id))

    def get_all_users(self) -> List[int]:
        """Отримання списку всіх ID користувачів"""
        return [int(user_id) for user_id in self.users.keys()]

# Створюємо глобальний екземпляр для використання в інших файлах
user_data = UserData() 