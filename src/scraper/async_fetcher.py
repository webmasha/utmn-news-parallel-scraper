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
        categories: list[dict] | None,
        concurrency: int,
        timeout: int,
        user_agent: str,
        request_delay: float,
        html_queue: asyncio.Queue,
        use_local_html: bool = False,
    ):
        """
        Инициализирует экземпляр AsyncFetcher.

        Args:
            base_url: Базовый URL-адрес сайта с новостями.
            categories: Список словарей с категориями {'url': str, 'name': str}.
            concurrency: Максимальное количество одновременных запросов.
            timeout: Таймаут для каждого запроса в секундах.
            user_agent: Строка User-Agent для HTTP-запросов.
            request_delay: Задержка в секундах между запросами.
            html_queue: Очередь `asyncio.Queue` для складирования полученного HTML.
            use_local_html: Использовать локальные HTML файлы для тестирования.
        """
        self.base_url = base_url
        self.categories = categories or []
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.html_queue = html_queue
        self.use_local_html = use_local_html
        self.local_files = {
            "https://news.utmn.ru/news/stories/": "../../../../2/main_news_page.html",
            "https://news.utmn.ru/news/stories/nauka-i-innovatsii/": "../../../../2/1.html",
            # Для новостей использовать single_news_page.html
        }
        self.default_news_file = "../../../../2/single_news_page.html"
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        """Инициализирует сессию `aiohttp` при входе в контекстный менеджер."""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.session = aiohttp.ClientSession(
            headers=headers, timeout=self.timeout
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
            if self.use_local_html:
                # Определяем файл: для категорий - соответствующий, для новостей - single_news_page.html
                if '/news/stories/' in url and url.rstrip('/').split('/')[-1].isdigit():
                    file_path = self.default_news_file
                else:
                    file_path = self.local_files.get(url.rstrip('/'), self.local_files.get("https://news.utmn.ru/news/stories/"))
                try:
                    import os
                    full_path = os.path.join(os.path.dirname(__file__), file_path)
                    with open(full_path, 'r', encoding='utf-8') as f:
                        logger.info("Чтение локального файла для %s: %s", url, full_path)
                        return f.read()
                except Exception as e:
                    logger.error("Ошибка чтения файла %s: %s", full_path, e)
                    return None
            else:
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

        Сначала загружает главную страницу новостей и страницы категорий,
        находит на них ссылки на отдельные новостные статьи, а затем
        асинхронно загружает каждую из них.

        Args:
            max_pages: Максимальное количество страниц для сбора. Если None,
                        собираются все найденные на главной странице ссылки.
        """

        # Список URL для парсинга: главная + категории
        urls_to_crawl = [self.base_url] + [cat['url'] for cat in self.categories]

        # Собираем все ссылки на новости
        all_news_links = []
        for url in urls_to_crawl:
            links = await self.crawl_category(url, max_pages)
            all_news_links.extend(links)
            if max_pages and len(all_news_links) >= max_pages:
                all_news_links = all_news_links[:max_pages]
                break

        logger.info("Найдено %d ссылок на новости для сбора.", len(all_news_links))

        # Создаем задачи для асинхронной загрузки всех найденных страниц
        tasks = [self.produce(link) for link in all_news_links]
        await asyncio.gather(*tasks)

    async def crawl_category(self, category_url: str, max_pages: int | None = None) -> list[str]:
        """
        Парсит одну категорию новостей, включая пагинацию.

        Args:
            category_url: URL категории.
            max_pages: Максимальное количество страниц.

        Returns:
            Список ссылок на новости.
        """
        news_links = []
        page = 1

        while True:
            # Формируем URL страницы (для первой страницы без PAGEN_1)
            if page == 1:
                url = category_url
            else:
                url = f"{category_url}?PAGEN_1={page}"

            logger.info("Загружаем страницу категории: %s", url)
            page_html = await self.fetch_page(url)
            if not page_html:
                logger.warning("Не удалось загрузить страницу %s", url)
                break

            # Парсим страницу для извлечения ссылок
            soup = BeautifulSoup(page_html, "lxml")
            page_links = []
            for a in soup.select("div.article_title > a"):
                if 'href' in a.attrs:
                    link = a['href']
                    full_link = urljoin(category_url, link)
                    if full_link not in news_links:  # Избегаем дубликатов
                        page_links.append(full_link)

            if not page_links:
                logger.info("На странице %s новостей не найдено", url)
                break

            news_links.extend(page_links)

            # Проверяем, есть ли следующая страница
            load_more_button = soup.select_one("button#btn_get-news")
            if not load_more_button or (max_pages and len(news_links) >= max_pages):
                break

            page += 1

        return news_links

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
