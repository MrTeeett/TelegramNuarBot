import json
import os
import sys
from telegram_bot import run_telegram_bot

# Определяем путь к settings.json
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

def load_settings():
    """Загружает настройки из settings.json, создаёт файл, если его нет."""
    if not os.path.exists(SETTINGS_FILE):
        print("⚠️  Файл настроек не найден! Создаю settings.json...")

        # Создаём файл с пустым токеном
        default_settings = {
            "TELEGRAM_BOT_TOKEN": ""
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=4)

        print(f"✅ Файл {SETTINGS_FILE} создан. 🔴 Введите свой токен в этот файл и перезапустите программу!")
        sys.exit(1)  # Завершаем программу, чтобы пользователь мог ввести токен

    # Загружаем настройки
    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)

    # Проверяем, есть ли в файле нужный ключ
    if "TELEGRAM_BOT_TOKEN" not in settings or not settings["TELEGRAM_BOT_TOKEN"]:
        print(f"⚠️  В файле {SETTINGS_FILE} отсутствует TELEGRAM_BOT_TOKEN или он пуст. 🔴 Введите токен и перезапустите программу!")
        sys.exit(1)

    return settings

if __name__ == '__main__':
    settings = load_settings()
    TELEGRAM_BOT_TOKEN = settings["TELEGRAM_BOT_TOKEN"]
    
    run_telegram_bot(TELEGRAM_BOT_TOKEN)
