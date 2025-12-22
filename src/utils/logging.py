import logging
import sys
import yaml
from pathlib import Path

def setup_logging():
    """
    Настраивает конфигурацию логирования для всего приложения.

    Функция выполняет следующие действия:
    1. Ищет файл `config.yaml` в корневой директории проекта.
    2. Если файл не найден, устанавливает базовую конфигурацию логирования
       с уровнем INFO и выводом в `sys.stdout`.
    3. Если файл найден, загружает секцию `logging` из него.
    4. Устанавливает уровень, формат и поток вывода логов на основе
       конфигурации.
    5. Понижает уровень логирования для слишком "шумных" библиотек
       (`aiosqlite`, `aiohttp`) до WARNING, чтобы не засорять вывод.
    """
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if not config_path.exists():
        # Конфигурация по умолчанию, если файл не найден
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        return

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f).get('logging', {})
    
    logging.basicConfig(
        level=config.get('level', 'INFO').upper(),
        format=config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        stream=sys.stdout  # Можно также настроить вывод в файл
    )
    # Уменьшаем "шум" от сторонних библиотек
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

