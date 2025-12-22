from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def parse_news_page(html: str, url: str) -> dict | None:
    """
    Извлекает структурированную информацию со страницы новости.

    Эта функция является "чистой" и ресурсоемкой (CPU-bound), что делает ее
    идеальным кандидатом для выполнения в отдельном процессе через
    `ProcessPoolExecutor`, чтобы не блокировать основной асинхронный цикл.

    Args:
        html: Строка, содержащая HTML-код страницы.
        url: URL-адрес страницы, с которой был получен HTML.

    Returns:
        Словарь с извлеченными данными: `url`, `title`, `date`, `section`,
        `summary`, `content`.
        В случае ошибки парсинга возвращает `None`.
    """
    try:
        soup = BeautifulSoup(html, "lxml")

        # Извлечение заголовка новости
        title_tag = soup.select_one(".article-detail__title h1")
        title = title_tag.text.strip() if title_tag else ""
        logger.debug(f"Parsed title: {title}")

        # Извлечение даты публикации
        date_day_tag = soup.select_one(".cat-n-views .date .day a")
        date_month_tag = soup.select_one(".cat-n-views .date .month")
        day = date_day_tag.text.strip() if date_day_tag else ""
        month = date_month_tag.text.strip() if date_month_tag else ""
        date_str = f"{day} {month}".strip()
        logger.debug(f"Parsed date: {date_str}")

        # Извлечение раздела (категории) новости
        section_tag = soup.select_one(".cat-n-views .category_title a")
        section = section_tag.text.strip() if section_tag else ""
        logger.debug(f"Parsed section: {section}")

        # Извлечение краткого содержания (лида)
        summary_tag = soup.select_one(".article-detail__preview")
        summary = summary_tag.text.strip() if summary_tag else ""
        logger.debug(f"Parsed summary: {summary}")

        # Извлечение полного текста новости
        content_div = soup.select_one(".article-detail_text")
        content = content_div.text.strip() if content_div else ""
        logger.debug(f"Parsed content length: {len(content)}")

        # Возвращаем результат, только если все ключевые поля были найдены
        if title and date_str and section and content:
            return {
                "url": url,
                "title": title,
                "date": date_str,
                "section": section,
                "summary": summary,
                "content": content,
            }
        else:
            logger.warning(f"Не удалось полностью распарсить страницу: {url}. Пропускаем.")
            return None

    except Exception as e:
        logger.error("Ошибка парсинга страницы %s: %s", url, e)
        return None
