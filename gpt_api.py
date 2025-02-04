import g4f
import g4f.Provider
import g4f.providers
import g4f.providers.base_provider
import g4f.providers.create_images
import tiktoken
import logging

class LanguageModelGPT:
    def __init__(self, model=g4f.models.gpt_4o_mini):
        self.model = model
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, messages):
        """Подсчёт количества токенов в списке сообщений"""
        return sum(len(self.tokenizer.encode(msg["content"])) for msg in messages)
    
    def get_response(self, messages):
        """
        1) Первый вызов ChatCompletion: получаем основной текст-ответ
        2) Второй вызов ChatCompletion: генерируем промпт для картинки
        3) Далее вызываем client.images.generate(...) с этим промптом
        """
        token_count = self.count_tokens(messages)
        logging.info(f"Количество токенов: {token_count}")

        # 1) Основной текст
        response = g4f.ChatCompletion.create(
            model=g4f.models.deepseek_v3,
            messages=messages
        )

        m = messages
        m.append({"role": "assistant", "content": response})

        mm = [
                {
                    "role": "system",
                    "content": (
                        "Ты опытный сценарист, создающий описания для нуарных сцен в стиле детектива. "
                        "На основе всего диалога между пользователем и Элеонорой 'Лео' Грей "
                        "составь атмосферное описание сцены, в которой происходит их разговор. "
                        "составь описание как можно более подробно и если в кадре есть Элеонора 'Лео' Грей обязательно скажи это и опиши ее внешность"
                        "Обязательно укажи:\n"
                        "- Имя персонажа Лео, место действия определи по контексту.\n"
                        "- Детали окружения: дождь, старый стол, сигаретный дым, бумажные дела и прочее что подходит по контексту.\n"
                        "- Эмоции и позу собеседников.\n"
                        "- Настроение нуарного детектива."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        "На основе контекста диалога создай текст для изображения, описывающий сцену беседы. "
                        "Важно передать атмосферу старого детективного офиса в Эдинбурге, где Лео беседует с клиентом."
                        "\n\nИстория общения:\n"
                        + "\n".join(f"{msg['role']}: {msg['content']}" for msg in m)
                    )
                }
            ]
        
        print(mm)

        response_image_prompt = g4f.ChatCompletion.create(
            model=g4f.models.deepseek_v3,
            messages=mm
        )

        print(response_image_prompt)

        # 3) Генерация картинки
        client = g4f.Client()
        image = client.images.generate(
            model="flux",
            prompt=response_image_prompt,  # Используем новый промпт
            response_format="url"
        )

        # Если всё ок, возвращаем (текстовый ответ, URL картинки)
        return response, image.data[0].url
