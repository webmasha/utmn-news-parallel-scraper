import asyncio
import logging
from typing import Awaitable, Callable
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class AsyncFetcher:
    """
    Асинхронный сборщик новостных страниц.

    Этот класс отвечает за асинхронную загрузку веб-страниц с новостями.
    Он использует `aiohttp` для выполнения HTTP-запросов и `asyncio.Semaphore`
    для ограничения количества одновременных подключений к серверу,
    чтобы избежать его перегрузки.

    Attributes:
        base_url: Базовый URL-адрес для сбора новостей.
        semaphore: Семафор для контроля конкурентных запросов.
        timeout: Таймаут для HTTP-запросов.
        user_agent: User-Agent для HTTP-заголовков.
        request_delay: Задержка между запросами.
        html_queue: Очередь `asyncio.Queue` для передачи HTML-кода парсерам.
        session: Клиентская сессия `aiohttp`.
    """

    def __init__(
        self,
        base_url: str,
        concurrency: int,
        timeout: int,
        user_agent: str,
        request_delay: float,
        html_queue: asyncio.Queue,
    ):
        """
        Инициализирует экземпляр AsyncFetcher.

        Args:
            base_url: Базовый URL-адрес сайта с новостями.
            concurrency: Максимальное количество одновременных запросов.
            timeout: Таймаут для каждого запроса в секундах.
            user_agent: Строка User-Agent для HTTP-запросов.
            request_delay: Задержка в секундах между запросами.
            html_queue: Очередь `asyncio.Queue` для складирования полученного HTML.
        """
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.html_queue = html_queue
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Инициализирует сессию `aiohttp` при входе в контекстный менеджер."""
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent}, timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрывает сессию `aiohttp` при выходе из контекстного менеджера."""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> str | None:
        """
        Загружает одну страницу и возвращает ее HTML-содержимое.

        Использует семафор для ограничения одновременных запросов и
        обрабатывает возможные ошибки сети или таймауты.

        Args:
            url: URL-адрес страницы для загрузки.

        Returns:
            Строку с HTML-кодом страницы или None в случае ошибки.
        """
        await asyncio.sleep(self.request_delay)
        async with self.semaphore:
            try:
                if not self.session:
                    raise ConnectionError("Сессия не инициализирована. Используйте 'async with'")
                
                logger.info("Загрузка страницы: %s", url)
                async with self.session.get(url) as response:
                    response.raise_for_status()  # Проверка на HTTP ошибки (4xx/5xx)
                    return await response.text()
            except aiohttp.ClientError as e:
                logger.error("HTTP ошибка при загрузке %s: %s", url, e)
                return None
            except asyncio.TimeoutError:
                logger.error("Таймаут при загрузке %s", url)
                return None

    async def crawl(self, max_pages: int | None = None):
        """
        Выполняет обход новостного сайта и помещает HTML-код страниц в очередь.

        Сначала загружает главную страницу новостей, находит на ней ссылки
        на отдельные новостные статьи, а затем асинхронно загружает
        каждую из них.

        Args:
            max_pages: Максимальное количество страниц для сбора. Если None,
                       собираются все найденные на главной странице ссылки.
        """
        
        # Загружаем главную страницу, чтобы найти ссылки на новости
        main_page_html = await self.fetch_page(self.base_url)
        if not main_page_html:
            logger.critical("Не удалось загрузить главную страницу новостей. Сбор прерван.")
            return

        # Парсим главную страницу для извлечения ссылок
        soup = BeautifulSoup(main_page_html, "lxml")
        news_links = []
        # Ищем ссылки на новости, используя новый CSS-селектор
        for a in soup.select("div.article_title > a"):
            if 'href' in a.attrs:
                link = a['href']
                # Корректно формируем абсолютную ссылку
                full_link = urljoin(self.base_url, link)
                news_links.append(full_link)
                # Ограничиваем количество ссылок, если задан max_pages
                if max_pages and len(news_links) >= max_pages:
                    break
        
        logger.info("Найдено %d ссылок на новости для сбора.", len(news_links))

        # Создаем задачи для асинхронной загрузки всех найденных страниц
        tasks = [self.produce(link) for link in news_links]
        await asyncio.gather(*tasks)

    async def produce(self, url: str):
        """
        Загружает страницу новости и помещает ее содержимое в очередь `html_queue`.

        Эта функция выступает в роли "производителя" (producer) в паттерне
        Producer-Consumer.

        Args:
            url: URL-адрес страницы для загрузки.
        """
        html = await self.fetch_page(url)
        if html:
            # Помещаем кортеж (HTML, URL) в очередь для дальнейшей обработки
            await self.html_queue.put((html, url))
            print(f"Помещен в очередь: {url}")
