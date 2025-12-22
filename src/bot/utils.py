from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def format_news_message(news_item: dict) -> str:
    """
    Форматирует новостную статью в строку для отправки в Telegram.

    Использует Markdown-разметку для выделения заголовка, даты и другой
    информации, делая сообщение более читабельным.

    Args:
        news_item: Словарь с данными о новости. Должен содержать
                   ключи 'title', 'date', 'section', 'summary', 'url'.

    Returns:
        Отформатированная строка, готовая к отправке.
    """
    return (
        f"*{news_item['title']}*\n\n"
        f"_{news_item['date']}_ | {news_item['section']}\n\n"
        f"{news_item['summary']}\n\n"
        f"[Читать далее]({news_item['url']})"
    )

def get_pagination_keyboard(
    current_offset: int,
    total_news: int,
    limit: int,
    section: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> InlineKeyboardMarkup | None:
    """
    Создает инлайн-клавиатуру для навигации по страницам новостей.

    Генерирует кнопки "Вперед" и "Назад", если это необходимо.
    В `callback_data` кнопок сохраняются текущие фильтры (раздел, даты),
    чтобы они не сбрасывались при переходе по страницам.

    Args:
        current_offset: Текущее смещение (количество уже просмотренных новостей).
        total_news: Общее количество новостей по текущему запросу.
        limit: Количество новостей на одной странице.
        section: Текущий фильтр по разделу.
        start_date: Текущий фильтр по начальной дате.
        end_date: Текущий фильтр по конечной дате.

    Returns:
        Объект `InlineKeyboardMarkup` с кнопками пагинации или `None`,
        если пагинация не требуется.
    """
    buttons = []
    
    # Собираем callback_data, сохраняя фильтры для следующего запроса
    callback_data_parts = ["page", "{offset}"]
    if section:
        callback_data_parts.append(f"s:{section}")
    if start_date:
        callback_data_parts.append(f"sd:{start_date}")
    if end_date:
        callback_data_parts.append(f"ed:{end_date}")
    
    callback_template = "_".join(callback_data_parts)

    # Кнопка "Назад", если это не первая страница
    if current_offset > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=callback_template.format(offset=current_offset - limit),
            )
        )
    # Кнопка "Вперед", если еще есть новости для отображения
    if current_offset + limit < total_news:
        buttons.append(
            InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=callback_template.format(offset=current_offset + limit),
            )
        )
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) if buttons else None

