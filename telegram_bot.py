# telegram_bot.py
import logging
import os
import re
import asyncio
import time
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from gpt_api import LanguageModelGPT
from conversation_manager import ConversationManager

# Создаём папку log, если её нет
LOG_DIR = "log"
os.makedirs(LOG_DIR, exist_ok=True)

# Настройка логирования в файл и консоль
LOG_FILE = os.path.join(LOG_DIR, "bot.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),  # Лог в файл
        logging.StreamHandler()  # Лог в консоль
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

with open("SYSTEM_MESSAGE.txt", "r", encoding="utf-8") as f:
    SYSTEM_MESSAGE = f.read()

# Инициализация API и менеджера диалогов
lm_api = LanguageModelGPT()
conv_manager = ConversationManager(storage_file="conversations.json")

# Глобальные словари для хранения очередей и задач для каждого пользователя
user_queues = {}
user_tasks = {}

def convert_markdown_to_html(text: str) -> str:
    """Преобразует текст в Markdown-разметке в HTML для Telegram"""
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)  # Жирный текст (**текст** → <b>текст</b>)
    text = re.sub(r"\*(.*?)\*", r"<i>\1</i>", text)      # Курсив (*текст* → <i>текст</i>)
    return text

async def generate_ambiance_text(lm_api, system_message: str) -> str:
    """
    Формирует запрос к AI, чтобы сгенерировать атмосферный текст от лица Лео.
    Возвращает HTML-текст, готовый к отправке в Telegram.
    """
    import g4f
    
    loop = asyncio.get_running_loop()
    
    # Пример сообщения, как просить AI сгенерировать атмосферу.
    # Можно отредактировать под свои нужды: где-то добавить конкретные указания, тематику, стиль и т.д.
    messages = [
        {
            "role": "system",
            "content": system_message  # Ваш большой SYSTEM_MESSAGE cо всей историей Лео
        },
        {
            "role": "user",
            "content": (
                "Сгенерируй короткий атмосферный текст в стиле детективного нуара, "
                "от лица Элеоноры 'Лео' Грей (29-летняя детектив из Эдинбурга). "
                "Сделай его приветствием для нового клиента, который только что вошёл в офис. "
                "Несколько предложений, чтобы погрузить в антураж."
                "Дя выделения текста используй знаки в Telegramm"
            )
        }
    ]

    # Синхронный вызов AI оборачиваем в executor:
    ambiance_text = await loop.run_in_executor(None, lm_api.get_response, messages, g4f.models.deepseek_v3)
    return ambiance_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    logger.info(f"Пользователь {user_id} начал беседу.")
    
    # Очищаем предыдущую переписку
    conv_manager.clear_conversation(user_id)
    
    # Устанавливаем в истории system_message
    new_history = [{"role": "system", "content": SYSTEM_MESSAGE}]
    conv_manager.update_conversation(user_id, new_history)

    # Короткое приветственное сообщение
    await update.message.reply_text(
        "Если хочешь очистить историю, используй /reset."
    )

    # 1. Запускаем фоновую задачу, которая показывает "печатает..."
    typing_task = asyncio.create_task(send_typing_action(update))

    try:
        # 2. Генерируем атмосферный текст через AI
        ambiance_text = await generate_ambiance_text(lm_api, SYSTEM_MESSAGE)
    finally:
        # 3. Останавливаем задачу "печатает..."
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

    # 4. Отправляем атмосферный текст
    await update.message.reply_text(ambiance_text)



async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    conv_manager.clear_conversation(user_id)
    logger.info(f"История пользователя {user_id} очищена.")
    await update.message.reply_text("История переписки очищена.")

async def get_response_async(history):
    loop = asyncio.get_running_loop()
    response_text = await loop.run_in_executor(None, lm_api.get_response, history)
    return response_text

async def send_typing_action(update):
    """Фоновая задача: отправляет статус "печатает" каждые 3 секунды, пока не остановлена."""
    try:
        while True:
            await update.message.chat.send_action(action=ChatAction.TYPING)
            await asyncio.sleep(3)  # Интервал отправки "печатает..."
    except asyncio.CancelledError:
        pass  # Если задача отменена, просто выходим

async def process_user_queue(user_id, queue: asyncio.Queue):
    """Обрабатывает сообщения конкретного пользователя из очереди."""
    max_attempts = 3  # Количество повторных попыток
    
    while True:
        update = await queue.get()
        user_text = update.message.text.strip()

        if not user_text:
            await update.message.reply_text("Не понял тебя. Попробуй сформулировать иначе.")
            queue.task_done()
            continue

        # Получаем историю переписки
        history = conv_manager.get_conversation(user_id)
        if not history:
            history.append({"role": "system", "content": SYSTEM_MESSAGE})
        
        # Добавляем сообщение пользователя
        history.append({"role": "user", "content": user_text})

        logger.info(f"Пользователь {user_id} отправил запрос в AI: {user_text}")

        response_text = ""
        start_time = time.time()

        # Запускаем "бот печатает..." как фоновую задачу (будет работать до cancel())
        typing_task = asyncio.create_task(send_typing_action(update))

        try:
            for attempt_num in range(max_attempts):
                try:
                    logger.info(f"Пользователь {user_id} - попытка {attempt_num+1}")
                    
                    # Запрашиваем ответ
                    response_text = await get_response_async(history)
                    if response_text and response_text.strip():
                        # Если получили непустой ответ, выходим из цикла
                        break

                except Exception as e:
                    logger.error(f"Ошибка на попытке {attempt_num+1} для пользователя {user_id}: {e}")
                    # НЕ отправляем сообщение об ошибке пользователю, просто логируем и идём на следующую попытку

        finally:
            # Останавливаем "бот печатает..."
            typing_task.cancel()
            try:
                await typing_task
            except asyncio.CancelledError:
                pass

        elapsed_time = time.time() - start_time
        logger.info(f"Пользователь {user_id} получил ответ за {elapsed_time:.2f} секунд")

        # Если после всех попыток нет результата — fallback
        if not response_text or not response_text.strip():
            response_text = "Хм... Я затрудняюсь ответить. Попробуй задать вопрос по-другому."

        # Добавляем ответ ассистента в историю и сохраняем
        history.append({"role": "assistant", "content": response_text})
        conv_manager.update_conversation(user_id, history)

        # Логируем и отправляем пользователю
        logger.info(f"{convert_markdown_to_html(response_text)}")
        await update.message.reply_text(response_text)

        # Сигнализируем, что очередь обработана
        queue.task_done()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id 

    # Если для этого пользователя ещё не создана очередь, создаём её и запускаем обработку
    if user_id not in user_queues:
        queue = asyncio.Queue()
        user_queues[user_id] = queue
        user_tasks[user_id] = asyncio.create_task(process_user_queue(user_id, queue))
    else:
        queue = user_queues[user_id]

    # Помещаем новое сообщение в очередь пользователя
    await queue.put(update)

def run_telegram_bot(token):
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    logger.info("Бот запущен и ждёт сообщений...")
    app.run_polling()
