import pytest
import asyncio
from src.scraper.storage import NewsStorage

@pytest.fixture
async def memory_storage() -> NewsStorage:
    """
    Фикстура для создания чистой базы данных SQLite в памяти для каждого теста.

    Использование БД в памяти (`:memory:`) обеспечивает изоляцию тестов
    и высокую скорость выполнения, так как не происходит обращения к файловой системе.

    Yields:
        Экземпляр NewsStorage с инициализированной БД в памяти.
    """
    storage = NewsStorage(":memory:")
    await storage.initialize()
    return storage

@pytest.mark.asyncio
async def test_save_and_get_news(memory_storage: NewsStorage):
    """
    Тестирует базовые операции сохранения и извлечения новости.

    Проверяет, что новость корректно сохраняется и может быть извлечена.
    Также проверяет, что ограничение уникальности по `url` работает
    и дубликаты не создаются.

    Args:
        memory_storage: Фикстура с БД в памяти.
    """
    news_item = {
        "url": "http://example.com/news/1",
        "title": "Тестовая новость",
        "date": "2024-01-01",
        "section": "тестирование",
        "summary": "Это тест.",
        "content": "Полное содержание теста.",
    }
    
    await memory_storage.save_news(news_item)
    
    # Проверка извлечения
    retrieved_news = await memory_storage.get_news(section="тестирование")
    assert len(retrieved_news) == 1
    assert retrieved_news[0]["title"] == "Тестовая новость"

    # Проверка уникальности: повторное сохранение не должно создавать дубликат
    await memory_storage.save_news(news_item)
    retrieved_news_after_resave = await memory_storage.get_news(section="тестирование")
    assert len(retrieved_news_after_resave) == 1

@pytest.mark.asyncio
async def test_get_news_filtering(memory_storage: NewsStorage):
    """
    Тестирует возможности фильтрации метода `get_news`.

    Проверяет корректность фильтрации по разделу, диапазону дат,
    а также по их комбинации.

    Args:
        memory_storage: Фикстура с БД в памяти.
    """
    news_items = [
        {"url": "http://example.com/news/1", "title": "Новость из науки 1", "date": "2024-01-05", "section": "наука", "summary": "", "content": ""},
        {"url": "http://example.com/news/2", "title": "Новость из технологий", "date": "2024-01-10", "section": "технологии", "summary": "", "content": ""},
        {"url": "http://example.com/news/3", "title": "Новость из науки 2", "date": "2024-01-15", "section": "наука", "summary": "", "content": ""},
    ]
    for item in news_items:
        await memory_storage.save_news(item)

    # Фильтрация по разделу
    science_news = await memory_storage.get_news(section="наука")
    assert len(science_news) == 2
    
    # Фильтрация по дате
    jan_news = await memory_storage.get_news(start_date="2024-01-01", end_date="2024-01-12")
    assert len(jan_news) == 2
    # Проверяем правильность сортировки (сначала более новые)
    assert jan_news[0]['title'] == 'Новость из технологий'

    # Комбинированная фильтрация по разделу и дате
    science_jan_news = await memory_storage.get_news(section="наука", start_date="2024-01-01", end_date="2024-01-12")
    assert len(science_jan_news) == 1
    assert science_jan_news[0]['title'] == 'Новость из науки 1'
