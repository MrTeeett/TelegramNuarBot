import json
import os
import logging

class ConversationManager:
    def __init__(self, storage_file="conversations.json"):
        self.storage_file = storage_file
        self.conversations = {}
        self.load_conversations()

    def load_conversations(self):
        """ Загружает историю переписки из файла, если он существует. """
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r", encoding="utf-8") as f:
                    self.conversations = json.load(f)
                logging.info(f"История загружена из {self.storage_file}")
            except json.JSONDecodeError as e:
                logging.error(f"Ошибка загрузки JSON: {e} - Файл повреждён. Создаём новый.")
                self.conversations = {}
                self.save_conversations()
            except Exception as e:
                logging.error(f"Ошибка при загрузке истории: {e}")
                self.conversations = {}

    def save_conversations(self):
        """ Сохраняет историю переписки в JSON-файл. """
        try:
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
            logging.info(f"Файл {self.storage_file} успешно сохранён.")
        except Exception as e:
            logging.error(f"Ошибка при сохранении JSON-файла: {e}")

    def get_conversation(self, user_id):
        """ Возвращает список сообщений пользователя. """
        return self.conversations.get(str(user_id), [])

    def update_conversation(self, user_id, messages):
        """ Обновляет историю переписки для пользователя. """
        logging.info(f"Обновляем историю для пользователя {user_id}")
        self.conversations[str(user_id)] = messages
        self.save_conversations()

    def clear_conversation(self, user_id):
        """ Очищает историю переписки пользователя. """
        if str(user_id) in self.conversations:
            self.conversations[str(user_id)] = []
            self.save_conversations()
