import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from src.scraper.storage import NewsStorage
from src.bot.utils import format_news_message, get_pagination_keyboard

logger = logging.getLogger(__name__)
router = Router()

# Количество новостей, отображаемых на одной странице
NEWS_PAGE_SIZE = 5

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start.

    Отправляет приветственное сообщение пользователю.

    Args:
        message: Объект сообщения от пользователя.
    """
    await message.answer(
        "Привет! Я бот, который умеет получать новости с сайта UTMN.\n"
        "Используйте /help, чтобы увидеть доступные команды."
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help.

    Отправляет справочную информацию по использованию команд.

    Args:
        message: Объект сообщения от пользователя.
    """
    await message.answer(
        "Доступные команды:\n"
        "/news [категория] [дата_начала] [дата_окончания] - Получить новости.\n"
        "Доступные категории:\n"
        "- Наука\n"
        "- Инновации\n"
        "- Образование\n"
        "- Международная деятельность\n"
        "- Студенческая деятельность\n"
        "Примеры:\n"
        "/news\n"
        "/news наука\n"
        "/news 01.01.2024 31.01.2024\n"
        "/news наука 01.01.2024 31.01.2024"
    )

@router.message(Command("news"))
async def cmd_news(message: Message, storage: NewsStorage):
    """
    Обработчик команды /news.

    Парсит аргументы команды (раздел, даты) и инициирует отправку
    первой страницы новостей.

    Args:
        message: Объект сообщения от пользователя.
        storage: Экземпляр NewsStorage, внедренный через middleware.
    """
    # Получаем аргументы из текста сообщения
    args = message.text.split()[1:]
    
    section, start_date, end_date = None, None, None
    
    # Очень простой парсинг аргументов, для реального приложения
    # лучше использовать более надежное решение (например, FSM).
    if len(args) == 1:
        if args[0].isalpha():
            section = args[0]
        else:
            # Обработка случая /news 01.01.2024 (не поддерживается напрямую)
            await message.answer("Пожалуйста, укажите корректную категорию или диапазон дат.")
            return
            
    elif len(args) == 2:
        start_date, end_date = args
    elif len(args) == 3:
        section, start_date, end_date = args

    # Отправляем первую страницу новостей
    await send_news_page(message, storage, section, start_date, end_date, offset=0)


async def send_news_page(
    message: Message,
    storage: NewsStorage,
    section: str | None,
    start_date: str | None,
    end_date: str | None,
    offset: int,
):
    """
    Отправляет пользователю страницу со списком новостей.

    Получает новости из хранилища, форматирует их и отправляет
    отдельными сообщениями. Также добавляет клавиатуру для пагинации.

    Args:
        message: Объект сообщения или callback-запроса для ответа.
        storage: Экземпляр NewsStorage.
        section: Фильтр по разделу.
        start_date: Фильтр по начальной дате.
        end_date: Фильтр по конечной дате.
        offset: Смещение для запроса к базе данных (пагинация).
    """
    # Получаем новости из БД
    news_items = await storage.get_news(
        section=section,
        start_date=start_date,
        end_date=end_date,
        limit=NEWS_PAGE_SIZE,
        offset=offset,
    )

    if not news_items:
        await message.answer("По вашему запросу новостей не найдено.")
        return

    # Небольшой хак для получения общего количества. В реальном приложении
    # лучше использовать отдельный запрос COUNT(*).
    total_news = len(await storage.get_news(section=section, start_date=start_date, end_date=end_date, limit=1000))

    # Отправляем каждую новость отдельным сообщением
    for item in news_items:
        await message.answer(
            format_news_message(item),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    
    # Создаем и отправляем клавиатуру для пагинации
    keyboard = get_pagination_keyboard(
        current_offset=offset,
        total_news=total_news,
        limit=NEWS_PAGE_SIZE,
        section=section,
        start_date=start_date,
        end_date=end_date,
    )
    if keyboard:
        await message.answer("Показать еще:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("page_"))
async def cq_page(callback_query: CallbackQuery, storage: NewsStorage):
    """
    Обработчик нажатий на инлайн-кнопки пагинации.

    Извлекает данные о смещении и фильтрах из `callback_data`,
    а затем вызывает `send_news_page` для отправки следующей/предыдущей
    страницы.

    Args:
        callback_query: Объект callback-запроса.
        storage: Экземпляр NewsStorage.
    """
    # Разбираем callback_data, чтобы получить смещение и фильтры
    parts = callback_query.data.split("_")
    
    offset = int(parts[1])
    
    # Восстанавливаем фильтры из callback_data
    section, start_date, end_date = None, None, None
    for part in parts[2:]:
        if part.startswith("s:"):
            section = part[2:]
        elif part.startswith("sd:"):
            start_date = part[3:]
        elif part.startswith("ed:"):
            end_date = part[3:]

    if callback_query.message:
      # Отправляем новую страницу новостей
      await send_news_page(
          callback_query.message, storage, section, start_date, end_date, offset=offset
      )
    # Отвечаем на callback, чтобы убрать "часики" на кнопке
    await callback_query.answer()
