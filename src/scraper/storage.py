import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class NewsStorage:
    """
    Класс для управления хранилищем новостей в базе данных SQLite.

    Предоставляет асинхронные методы для инициализации базы данных,
    сохранения и извлечения новостных статей.
    """
    def __init__(self, db_path: str):
        """
        Инициализирует экземпляр NewsStorage.

        Args:
            db_path: Путь к файлу базы данных SQLite.
        """
        self.db_path = db_path

    async def initialize(self):
        """
        Инициализирует базу данных и создает таблицу новостей, если она не существует.

        Этот метод подключается к базе данных SQLite, указанной в `db_path`,
        и выполняет SQL-запрос для создания таблицы `news`, если она еще не была создана.
        Таблица предназначена для хранения собранной информации о новостях.
        """
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    title TEXT,
                    date TEXT,
                    section TEXT,
                    summary TEXT,
                    content TEXT,
                    scraped_at TEXT
                )
                """
            )
            await db.commit()
        logger.info("База данных инициализирована: %s", self.db_path)

    async def save_news(self, news_item: dict):
        """
        Сохраняет одну новостную статью в базу данных.

        Если новость с таким же URL уже существует, она не будет добавлена
        повторно благодаря ограничению UNIQUE для поля url.

        Args:
            news_item: Словарь, содержащий данные о новости.
                       Ожидаемые ключи: "url", "title", "date", "section",
                       "summary", "content".
        """
        scraped_at = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """
                    INSERT INTO news (url, title, date, section, summary, content, scraped_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        news_item["url"],
                        news_item["title"],
                        news_item["date"],
                        news_item["section"],
                        news_item["summary"],
                        news_item["content"],
                        scraped_at,
                    ),
                )
                await db.commit()
                logger.debug("Новость сохранена: %s", news_item["url"])
            except aiosqlite.IntegrityError:
                logger.debug("Новость уже существует, пропуск: %s", news_item["url"])

    async def get_news(
        self,
        section: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 5,
        offset: int = 0,
    ) -> list[dict]:
        """
        Извлекает новости из базы данных с возможностью фильтрации и пагинации.

        Args:
            section: Раздел новостей для фильтрации.
            start_date: Начало диапазона дат (в формате ГГГГ-ММ-ДД).
            end_date: Конец диапазона дат (в формате ГГГГ-ММ-ДД).
            limit: Максимальное количество новостей для возврата.
            offset: Количество новостей, которые нужно пропустить (для пагинации).

        Returns:
            Список словарей, где каждый словарь представляет одну новость.
        """
        # Формируем базовый запрос
        query = "SELECT * FROM news"
        conditions = []
        params = []

        # Добавляем условия фильтрации, если они предоставлены
        if section:
            conditions.append("section LIKE ?")
            params.append(f"%{section}%")
        if start_date:
            conditions.append("date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date <= ?")
            params.append(end_date)

        # Собираем все условия в единый блок WHERE
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Добавляем сортировку, лимит и смещение для пагинации
        query += " ORDER BY date DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        # Выполняем асинхронный запрос к базе данных
        async with aiosqlite.connect(self.db_path) as db:
            # Используем aiosqlite.Row для получения результатов в виде словарей
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
            # Преобразуем строки в стандартные словари
            news_list = [dict(row) for row in rows]

            # Фильтруем по section case-insensitive, если section задан
            if section:
                section_lower = section.lower()
                news_list = [item for item in news_list if section_lower in item['section'].lower()]

            return news_list
