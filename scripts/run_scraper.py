import asyncio
import logging
import yaml
from pathlib import Path
import sys

# Добавляем корневую директорию проекта в sys.path
# Это необходимо для корректного импорта модулей, например, из `src/`.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.scraper.async_fetcher import AsyncFetcher
from src.scraper.queue_manager import QueueManager
from src.scraper.storage import NewsStorage

async def main():
    """
    Основная функция для запуска процесса сбора новостей.

    Этот скрипт координирует работу всех компонентов скрейпера:
    1. Загружает конфигурацию из файла `config.yaml`.
    2. Настраивает систему логирования.
    3. Инициализирует хранилище данных (`NewsStorage`).
    4. Создает асинхронную очередь (`asyncio.Queue`) для передачи HTML.
    5. Инициализирует сборщика (`AsyncFetcher`) и менеджера очереди (`QueueManager`).
    6. Запускает параллельно две основные задачи:
       - `producer_task`: задача-производитель, которая собирает HTML-страницы.
       - `consumer_task`: задача-потребитель, которая обрабатывает страницы из очереди.
    7. Ожидает завершения обеих задач.
    """
    # Загрузка конфигурации
    config_base_path = Path(__file__).parent.parent
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

    # Инициализация хранилища и базы данных
    db_path = config.get("db_path", "news.db")
    storage = NewsStorage(db_path)
    await storage.initialize()

    # Создание общей очереди для HTML-страниц
    html_queue = asyncio.Queue()

    # Настройка и создание экземпляра сборщика (продюсера)
    fetcher_config = config.get("scraper", {})
    fetcher = AsyncFetcher(
        base_url=config.get("news_url", "https://www.utmn.ru/news"),
        concurrency=fetcher_config.get("concurrency", 10),
        timeout=fetcher_config.get("timeout", 10),
        user_agent=fetcher_config.get("user_agent", "UTMN News Scraper/1.0"),
        request_delay=fetcher_config.get("request_delay", 0.1),
        html_queue=html_queue,
    )

    # Настройка и создание экземпляра менеджера очереди (потребителя)
    queue_manager = QueueManager(
        html_queue=html_queue,
        storage=storage,
        parsing_workers=fetcher_config.get("parsing_workers", 0),
    )

    # Запуск продюсера и потребителей в контексте сессии сборщика
    async with fetcher:
        # Создаем асинхронные задачи
        producer_task = asyncio.create_task(fetcher.crawl())
        consumer_task = asyncio.create_task(queue_manager.start_consumers())

        # Ожидаем завершения обеих задач
        await asyncio.gather(producer_task, consumer_task)

if __name__ == "__main__":
    asyncio.run(main())
