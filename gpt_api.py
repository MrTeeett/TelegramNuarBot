import g4f
import g4f.Provider
import g4f.providers
import g4f.providers.base_provider
import g4f.providers.create_images
import tiktoken
import logging
import re

class LanguageModelGPT:
    def __init__(self, model=g4f.models.deepseek_r1):
        self.model = model
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, messages):
        """Подсчёт количества токенов в списке сообщений"""
        return sum(len(self.tokenizer.encode(msg["content"])) for msg in messages)
    
    def get_response(self, messages, model = None):
        """
        1) Первый вызов ChatCompletion: получаем основной текст-ответ
        2) Второй вызов ChatCompletion: генерируем промпт для картинки
        3) Далее вызываем client.images.generate(...) с этим промптом
        """
        token_count = self.count_tokens(messages)
        logging.info(f"Количество токенов: {token_count}")
        
        if model == None:
            model = self.model

        # 1) Основной текст
        response = g4f.ChatCompletion.create(
            model=model,
            messages=messages
        )

        m = messages
        m.append({"role": "assistant", "content": response})
        print("\n\n\n Ответ перед выводом:", response, "\n\n\n")
        new_response = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL)
        print("\n\n\n Ответ для вывода:", new_response, "\n\n\n")


        # Если всё ок, возвращаем (текстовый ответ, URL картинки)
        return new_response
