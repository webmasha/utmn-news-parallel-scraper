import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
import os
from typing import Callable

from src.scraper.parser import parse_news_page
from src.scraper.storage import NewsStorage

logger = logging.getLogger(__name__)

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

    async def start_consumers(self):
        """
        Запускает задачи-потребители для парсинга HTML и сохранения данных.

        Создает пул процессов (`ProcessPoolExecutor`) и запускает в нем
        несколько задач `consume`, которые будут извлекать данные из очереди
        и обрабатывать их. Метод завершает работу, когда очередь становится
        пустой и все элементы обработаны.
        """
        logger.info("Запуск %d воркеров для парсинга.", self.parsing_workers)
        with ProcessPoolExecutor(max_workers=self.parsing_workers) as executor:
            # Создаем N асинхронных задач-потребителей
            tasks = []
            for _ in range(self.parsing_workers):
                task = self.loop.create_task(self.consume(executor))
                tasks.append(task)
            
            # Ожидаем, пока все элементы в очереди не будут обработаны
            await self.html_queue.join()

            # После обработки всех элементов отменяем задачи-потребители
            for task in tasks:
                task.cancel()
            
            # Ожидаем завершения всех отмененных задач
            await asyncio.gather(*tasks, return_exceptions=True)

    async def consume(self, executor: ProcessPoolExecutor):
        """
        Извлекает HTML из очереди, парсит его и сохраняет в хранилище.

        Эта функция является "потребителем" (consumer). Она работает в
        бесконечном цикле, ожидая новые данные в `html_queue`.
        Парсинг выполняется в отдельном процессе с помощью `run_in_executor`.

        Args:
            executor: Экземпляр `ProcessPoolExecutor` для выполнения
                      CPU-bound задач.
        """
        while True:
            try:
                html, url = await self.html_queue.get()
                
                # Запускаем CPU-bound функцию парсинга в отдельном процессе,
                # чтобы не блокировать основной цикл событий.
                result = await self.loop.run_in_executor(
                    executor, parse_news_page, html, url
                )
                
                if result:
                    await self.storage.save_news(result)

                # Сообщаем очереди, что задача выполнена
                self.html_queue.task_done()
            except asyncio.CancelledError:
                # Выход из цикла при отмене задачи
                break
            except Exception as e:
                logger.error("Ошибка в потребителе: %s", e)
                # В реальном приложении здесь можно реализовать логику
                # повторной обработки или перемещения в "очередь ошибок".
                self.html_queue.task_done()

