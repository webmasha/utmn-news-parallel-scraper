import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
import os
from typing import Callable
import yaml
from pathlib import Path

from src.scraper.parser import parse_news_page
from src.scraper.storage import NewsStorage

logger = logging.getLogger(__name__)

def init_worker():
    """Инициализатор для дочерних процессов, настраивающий логирование."""
    config_base_path = Path(__file__).parent.parent.parent
    config_local_path = config_base_path / "config.local.yaml"
    config_default_path = config_base_path / "config.yaml"

    if config_local_path.exists():
        with open(config_local_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        with open(config_default_path, "r") as f:
            config = yaml.safe_load(f)

    logging.basicConfig(
        level=config.get("logging", {}).get("level", "INFO").upper(),
        format="%(asctime)s - %(process)d - %(name)s - %(levelname)s - %(message)s"
    )

class QueueManager:
    """
    Управляет конвейером обработки новостей: от получения HTML до сохранения в БД.

    Этот класс связывает воедино асинхронных производителей (fetchers) и
    параллельных потребителей (parsers). Он организует пул процессов для
    выполнения ресурсоемких задач парсинга HTML, не блокируя основной
    асинхронный поток.

    Attributes:
        html_queue: Очередь `asyncio.Queue`, из которой потребители
                    берут HTML-страницы для обработки.
        storage: Экземпляр `NewsStorage` для сохранения результатов в базу данных.
        parsing_workers: Количество дочерних процессов для парсинга HTML.
        loop: Текущий цикл событий asyncio.
    """

    def __init__(
        self,
        html_queue: asyncio.Queue,
        storage: NewsStorage,
        parsing_workers: int,
    ):
        """
        Инициализирует QueueManager.

        Args:
            html_queue: Очередь `asyncio.Queue` для получения HTML.
            storage: Экземпляр `NewsStorage` для сохранения данных.
            parsing_workers: Количество воркеров для парсинга. Если 0,
                             количество определяется автоматически
                             (os.cpu_count()).
        """
        self.html_queue = html_queue
        self.storage = storage
        self.parsing_workers = parsing_workers if parsing_workers > 0 else os.cpu_count() or 1
        self.loop = asyncio.get_running_loop()

    async def start_consumers(self, executor):
        """
        Запускает задачи-потребители для парсинга HTML и сохранения данных.
        """
        logger.info("Запуск %d воркеров для парсинга.", self.parsing_workers)
        tasks = []
        for _ in range(self.parsing_workers):
            task = self.loop.create_task(self.consume(executor))
            tasks.append(task)
        return tasks

    async def consume(self, executor: ProcessPoolExecutor):
        """
        Извлекает HTML из очереди, парсит его и сохраняет в хранилище.
        """
        while True:
            try:
                html, url = await self.html_queue.get()
                print(f"Потребитель получил URL: {url}")
                
                print(f"Вызов парсера для URL: {url}")
                result = await self.loop.run_in_executor(
                    executor, parse_news_page, html, url
                )
                print(f"Парсер для URL {url} вернул: {'Успех' if result else 'Неудача'}")
                
                if result:
                    await self.storage.save_news(result)
                    print(f"Новость для URL {url} успешно сохранена.")
                else:
                    logger.debug(f"Парсер вернул None для {url}")

                self.html_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Ошибка в потребителе: %s", e)
                self.html_queue.task_done()
