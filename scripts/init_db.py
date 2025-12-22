import asyncio
import yaml
from pathlib import Path
import sys

# Добавляем корневую директорию проекта в sys.path
# Это необходимо для корректного импорта модулей, например, из `src/`.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.scraper.storage import NewsStorage

async def main():
    """
    Инициализирует базу данных для проекта.

    Этот скрипт выполняет следующие действия:
    1. Загружает конфигурацию из файла `config.yaml`.
    2. Извлекает путь к базе данных из конфигурации.
    3. Создает экземпляр `NewsStorage`.
    4. Вызывает метод `initialize()`, который создает таблицу `news`,
       если она еще не существует.
    """
    # Загрузка конфигурации
    config_base_path = Path(__file__).parent.parent
    config_local_path = config_base_path / "config.local.yaml"
    config_default_path = config_base_path / "config.yaml"

    if config_local_path.exists():
        with open(config_local_path, "r") as f:
            config = yaml.safe_load(f)
    else:
        with open(config_default_path, "r") as f:
            config = yaml.safe_load(f)

    # Создание и инициализация хранилища
    db_path = config.get("db_path", "news.db")
    storage = NewsStorage(db_path)
    await storage.initialize()

if __name__ == "__main__":
    # Запуск асинхронной функции main
    asyncio.run(main())
