from pathlib import Path
import pytest
from src.scraper.parser import parse_news_page

@pytest.fixture
def news_html_content() -> str:
    """
    Фикстура pytest, предоставляющая HTML-содержимое тестовой страницы.

    Читает и возвращает содержимое файла `test_data/news_page.html`.
    Это позволяет тестировать парсер на стабильных, неизменяемых данных.

    Returns:
        Строка с HTML-кодом.
    """
    path = Path(__file__).parent / "test_data" / "news_page.html"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def test_parse_news_page(news_html_content: str):
    """
    Тестирует корректность парсинга одной новостной страницы.

    Args:
        news_html_content: HTML-содержимое, предоставленное фикстурой.
    """
    url = "http://example.com/news/123"
    result = parse_news_page(news_html_content, url)

    assert result is not None
    assert result["url"] == url
    assert result["title"] == "Ученые ТюмГУ создали новый материал для очистки воды от нефтепродуктов"
    assert "25 декабря 2023" in result["date"]
    assert result["section"] == "Наука и исследования"
    assert result["summary"].startswith("Исследователи из Тюменского государственного университета")
    assert result["content"].startswith("Новый сорбент, разработанный в лаборатории")
