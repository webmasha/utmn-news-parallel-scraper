import asyncio
import logging
import os
import yaml
from pathlib import Path
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.commands import router
from src.scraper.storage import NewsStorage

async def main():
    """
    Основная асинхронная функция для запуска Telegram-бота.

    Выполняет следующие шаги:
    1. Загружает конфигурацию из файла `config.yaml`.
    2. Настраивает логирование.
    3. Получает токен бота из переменных окружения или конфигурационного файла.
    4. Инициализирует объекты бота, диспетчера и хранилища.
    5. Создает экземпляр `NewsStorage` для доступа к базе данных.
    6. Внедряет `NewsStorage` в контекст диспетчера, чтобы он был доступен
       в обработчиках команд.
    7. Регистрирует роутер с обработчиками команд.
    8. Запускает бота в режиме опроса (polling).
    """
    # Загрузка конфигурации
    config_base_path = Path(__file__).parent.parent.parent
    config_local_path = config_base_path / "config.local.yaml"
    config_default_path = config_base_path / "config.yaml"

    if config_local_path.exists():
        with open(config_local_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        with open(config_default_path, "r") as f:
            config = yaml.safe_load(f)

    # Настройка логирования
    logging.basicConfig(
        level=config.get("logging", {}).get("level", "INFO"),
        format=config.get("logging", {}).get(
            "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
    )

    # Получение токена. Приоритет у переменной окружения.
    token = os.getenv("TELEGRAM_TOKEN", config.get("telegram_token"))
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN":
        logging.critical("Токен Telegram не установлен. Укажите его в config.yaml или через переменную окружения TELEGRAM_TOKEN.")
        return

    # Инициализация основных объектов aiogram
    bot = Bot(token=token)
    storage = MemoryStorage()  # Используем хранилище в памяти для FSM
    dp = Dispatcher(storage=storage)

    # Инициализация хранилища новостей
    db_path = config.get("db_path", "news.db")
    news_storage = NewsStorage(db_path)
    
    # Внедрение зависимости (экземпляра NewsStorage) в диспетчер.
    # Теперь он будет доступен во всех обработчиках через аргумент `storage`.
    dp["storage"] = news_storage

    # Подключение роутера с командами
    dp.include_router(router)

    # Удаление старых вебхуков и запуск бота
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
