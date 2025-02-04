import os
import shutil
import subprocess

# Определяем пути
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))  # Корень проекта
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")

# Файлы, которые должны быть включены в сборку
FILES_TO_INCLUDE = [
    "SYSTEM_MESSAGE.txt",
    "conversation_manager.py",
    "gpt_api.py",
    "telegram_bot.py"
]

def clean():
    """Удаляет старые сборки и временные файлы"""
    print("[1/5] Очистка старых билдов и временных файлов...")
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

def install_dependencies():
    """Устанавливает зависимости"""
    print("[2/5] Установка зависимостей...")
    subprocess.run(["pip", "install", "-r", os.path.join(PROJECT_ROOT, "requirements.txt")], check=True)

def build_executable(target):
    """Собирает проект для указанной платформы"""
    print(f"[3/5] Компиляция для {target.capitalize()}...")

    # Формируем аргументы для PyInstaller
    command = [
        "pyinstaller",
        "--name", "ChatBot",
        "--onefile",
        "--distpath", os.path.join(BUILD_DIR, target),
        "--workpath", TEMP_DIR,
        "--specpath", TEMP_DIR,
        "--hidden-import", "g4f",
        "--hidden-import", "tiktoken",
        "--hidden-import", "curl_cffi",
        "--hidden-import", "telegram"
    ]

    # Добавляем файлы с абсолютными путями
    for file in FILES_TO_INCLUDE:
        abs_path = os.path.join(PROJECT_ROOT, file)
        if os.path.exists(abs_path):
            command.append(f"--add-data={abs_path};.")  # Windows
        else:
            print(f"⚠️ Предупреждение: Файл {file} не найден ({abs_path}) и не будет добавлен!")

    # Добавляем основной скрипт
    main_script = os.path.join(PROJECT_ROOT, "main.py")
    command.append(main_script)

    # Запускаем PyInstaller
    subprocess.run(command, check=True)

def main():
    """Основной процесс сборки"""
    clean()
    install_dependencies()

    import sys
    if len(sys.argv) > 1:
        target = sys.argv[1].lower()
        if target == "windows":
            build_executable("windows")
        elif target == "linux":
            build_executable("linux")
        else:
            print("❌ Ошибка: Неподдерживаемая платформа! Используйте 'windows' или 'linux'.")
    else:
        build_executable("windows")
        build_executable("linux")

if __name__ == "__main__":
    main()
