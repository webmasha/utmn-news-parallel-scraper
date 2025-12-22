import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.commands import router
from src.scraper.storage import NewsStorage

@pytest.fixture
async def memory_storage_for_bot() -> NewsStorage:
    """
    Фикстура, создающая и предзаполняющая БД в памяти для тестов бота.

    Yields:
        Экземпляр NewsStorage с одной тестовой новостью.
    """
    storage = NewsStorage(":memory:")
    await storage.initialize()
    # Предварительно заполняем данными для тестов
    await storage.save_news({
        "url": "http://example.com/news/1",
        "title": "Тестовая новость для бота",
        "date": "2024-02-01",
        "section": "боты",
        "summary": "Резюме",
        "content": "Содержание"
    })
    return storage

@pytest.fixture
def dispatcher() -> Dispatcher:
    """
    Фикстура, создающая экземпляр `Dispatcher` для тестирования.

    Returns:
        Экземпляр `aiogram.Dispatcher`.
    """
    return Dispatcher(storage=MemoryStorage())


@pytest.mark.asyncio
async def test_start_command(dispatcher: Dispatcher):
    """
    Тестирует обработчик команды `/start`.

    Args:
        dispatcher: Фикстура диспетчера.
    """
    dispatcher.include_router(router)
    
    bot = MagicMock()
    bot.send_message = AsyncMock()
    
    # Симулируем команду "/start"
    message = MagicMock()
    message.text = "/start"
    message.answer = AsyncMock()

    await dispatcher.feed_update(bot, {"message": message.to_python()})

    # Проверяем, что бот ответил правильным приветственным сообщением
    message.answer.assert_called_with(
        "Привет! Я бот, который умеет получать новости с сайта UTMN.\n"
        "Используйте /help, чтобы увидеть доступные команды."
    )

@pytest.mark.asyncio
async def test_news_command(dispatcher: Dispatcher, memory_storage_for_bot: NewsStorage):
    """
    Тестирует команду `/news` с использованием мок-хранилища.

    Проверяет, что бот корректно обрабатывает команду, обращается к хранилищу
    и отправляет в ответе найденную новость.

    Args:
        dispatcher: Фикстура диспетчера.
        memory_storage_for_bot: Фикстура с предзаполненной БД.
    """
    
    # Внедряем мок-хранилище в диспетчер
    dispatcher["storage"] = memory_storage_for_bot
    dispatcher.include_router(router)
    
    bot = MagicMock()
    bot.send_message = AsyncMock()

    message = MagicMock()
    message.text = "/news боты"
    message.answer = AsyncMock()

    # Обработчик команды вызовет `storage.get_news`.
    await dispatcher.feed_update(bot, {"message": message.to_python()})
    
    # Проверяем, что бот отправил сообщение, содержащее заголовок новости.
    # Это упрощенная проверка; в реальном тесте может потребоваться
    # более детальный анализ аргументов вызова.
    
    # Собираем все вызовы `message.answer`
    all_calls = message.answer.call_args_list
    
    # Ищем заголовок в аргументах вызовов
    found_title = False
    for call in all_calls:
        # call - это кортеж из (args, kwargs)
        if any("Тестовая новость для бота" in str(arg) for arg in call[0]):
            found_title = True
            break
        if any("Тестовая новость для бота" in str(val) for val in call[1].values()):
            found_title = True
            break

    assert found_title, "Заголовок новости не был найден ни в одном из ответов бота."
