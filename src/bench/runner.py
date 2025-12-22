import asyncio
import time
import logging
import os
import psutil
import json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List
import yaml # Import yaml for config loading
import sys

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import aiohttp
from bs4 import BeautifulSoup

from src.scraper.parser import parse_news_page
from src.scraper.storage import NewsStorage

# Настройка логирования для бенчмарков
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

NEWS_URL = config.get("news_url", "https://www.utmn.ru/news")
MAX_PAGES_TO_SCRAPE = 50  # Ограничение для скорости выполнения бенчмарков

async def get_news_links(session: aiohttp.ClientSession, max_pages: int) -> List[str]:
    """
    Получает список ссылок на новостные статьи с главной страницы.

    Args:
        session: Экземпляр `aiohttp.ClientSession`.
        max_pages: Максимальное количество ссылок для сбора.

    Returns:
        Список URL-адресов новостных статей.
    """
    try:
        async with session.get(NEWS_URL) as response:
            response.raise_for_status()
            html = await response.text()
            soup = BeautifulSoup(html, "lxml")
            links = []
            for a in soup.find_all("a", class_="news-list-item__title-link", limit=max_pages):
                link = a['href']
                if not link.startswith('http'):
                    link = NEWS_URL.rsplit('/', 1)[0] + link
                links.append(link)
            return links
    except aiohttp.ClientError as e:
        logging.error(f"Ошибка при получении ссылок на новости: {e}")
        return []

# --- Последовательный запуск ---
def fetch_and_parse_sequentially(links: List[str]):
    """
    Последовательно загружает и парсит страницы.

    Использует блокирующую библиотеку `requests` для имитации
    полностью синхронного выполнения.

    Args:
        links: Список URL-адресов для обработки.

    Returns:
        Список словарей с результатами парсинга.
    """
    results = []
    for url in links:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            parsed = parse_news_page(response.text, url)
            if parsed:
                results.append(parsed)
        except requests.RequestException as e:
            logging.error(f"Ошибка при последовательной загрузке {url}: {e}")
    return results

# --- Асинхронный запуск ---
async def fetch_async(session: aiohttp.ClientSession, url: str):
    """Асинхронно загружает одну страницу."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text(), url
    except aiohttp.ClientError as e:
        logging.error(f"Ошибка при асинхронной загрузке {url}: {e}")
        return None, url

async def run_async_benchmark(links: List[str]):
    """
    Запускает асинхронный бенчмарк.

    Все страницы загружаются асинхронно, а затем парсятся
    последовательно в основном потоке.

    Args:
        links: Список URL-адресов для обработки.

    Returns:
        Кортеж (результаты, время парсинга).
    """
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_async(session, link) for link in links]
        html_contents = await asyncio.gather(*tasks)
        
        parsing_start_time = time.time()
        results = [parse_news_page(html, url) for html, url in html_contents if html]
        parsing_time = time.time() - parsing_start_time
        
        return results, parsing_time

# --- Гибридный запуск (Асинхронный + Многопроцессорный) ---
async def run_hybrid_benchmark(links: List[str], workers: int):
    """
    Запускает гибридный бенчмарк.

    Страницы загружаются асинхронно и помещаются в очередь.
    Пул процессов параллельно извлекает HTML из очереди и парсит его.

    Args:
        links: Список URL-адресов для обработки.
        workers: Количество процессов-воркеров.

    Returns:
        Список словарей с результатами парсинга.
    """
    html_queue = asyncio.Queue()
    
    async def producer(session: aiohttp.ClientSession):
        """Асинхронно загружает страницы и кладет их в очередь."""
        for url in links:
            html, _ = await fetch_async(session, url)
            if html:
                await html_queue.put((html, url))

    results = []
    loop = asyncio.get_running_loop()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        async with aiohttp.ClientSession() as session:
            producer_task = asyncio.create_task(producer(session))
            
            # Упрощенная логика потребителя для бенчмарка
            tasks = []
            while not (producer_task.done() and html_queue.empty()):
                try:
                    html, url = await asyncio.wait_for(html_queue.get(), timeout=1.0)
                    future = loop.run_in_executor(executor, parse_news_page, html, url)
                    tasks.append(future)
                except asyncio.TimeoutError:
                    continue
            
            for future in as_completed(tasks):
                result = future.result()
                if result:
                    results.append(result)

            await producer_task  # Убедимся, что производитель закончил работу

    return results

def measure_performance(func, *args, **kwargs):
    """
    Измеряет время выполнения и использование ресурсов функцией.

    Args:
        func: Функция для измерения.
        *args, **kwargs: Аргументы для передаваемой функции.

    Returns:
        Словарь с результатами измерений.
    """
    process = psutil.Process(os.getpid())
    start_time = time.time()
    
    # Измеряем использование памяти до выполнения
    mem_before = process.memory_info().rss / 1024 / 1024  # в МБ
    
    # Выполняем функцию
    result = func(*args, **kwargs)
    
    # Измеряем использование памяти после выполнения
    mem_after = process.memory_info().rss / 1024 / 1024  # в МБ
    
    end_time = time.time()
    
    elapsed_time = end_time - start_time
    cpu_times = process.cpu_times()
    
    return {
        "result": result,
        "time_elapsed": elapsed_time,
        "cpu_user": cpu_times.user,
        "cpu_system": cpu_times.system,
        "mem_usage_mb": mem_after - mem_before
    }

async def main():
    """Основная функция для запуска всех бенчмарков."""
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)
    
    async with aiohttp.ClientSession() as session:
        links = await get_news_links(session, MAX_PAGES_TO_SCRAPE)

    if not links:
        logging.error("Нет ссылок для бенчмаркинга. Выход.")
        return

    all_results = {}

    # Последовательный режим
    # Примечание: Используем `requests` для простоты, хотя он блокирующий.
    # Это сделано для демонстрации концепции.
    import requests 
    logging.info("Запуск последовательного бенчмарка...")
    seq_perf = measure_performance(fetch_and_parse_sequentially, links)
    all_results["sequential"] = {
        "time": seq_perf["time_elapsed"],
        "cpu": seq_perf["cpu_user"],
        "memory": seq_perf["mem_usage_mb"],
    }
    logging.info(f"Последовательный режим завершен за {seq_perf['time_elapsed']:.2f}с")

    # Асинхронный режим
    logging.info("Запуск асинхронного бенчмарка...")
    async_start_time = time.time()
    _, parsing_time = await run_async_benchmark(links)
    async_total_time = time.time() - async_start_time
    all_results["async"] = {
        "time": async_total_time,
        "fetch_time": async_total_time - parsing_time,
        "parse_time": parsing_time
    }
    logging.info(f"Асинхронный режим завершен за {async_total_time:.2f}с")

    # Гибридный режим
    for workers in [1, 2, 4, os.cpu_count() or 1]:
        logging.info(f"Запуск гибридного бенчмарка с {workers} воркерами...")
        hybrid_start_time = time.time()
        await run_hybrid_benchmark(links, workers)
        hybrid_total_time = time.time() - hybrid_start_time
        all_results[f"hybrid_{workers}_workers"] = {"time": hybrid_total_time}
        logging.info(f"Гибридный режим ({workers} воркеров) завершен за {hybrid_total_time:.2f}с")

    # Сохранение результатов
    results_path = results_dir / f"benchmark_{int(time.time())}.json"
    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=4)
        
    logging.info(f"Результаты бенчмарка сохранены в {results_path}")

if __name__ == "__main__":
    # Примечание: для запуска последовательной части может потребоваться
    # `pip install requests`. Он не включен в pyproject.toml,
    # чтобы не загрязнять зависимости основного проекта.
    try:
        import requests
    except ImportError:
        logging.warning("Библиотека `requests` не найдена. Пропуск последовательного бенчмарка.")
        # Простая "заглушка", чтобы избежать падения
        def fetch_and_parse_sequentially(links): return []

    asyncio.run(main())
