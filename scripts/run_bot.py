import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
# Это необходимо для корректного импорта модулей, например, из `src/`.
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.bot.main import main as run_bot

# Этот скрипт является точкой входа для запуска Telegram-бота.
# Он импортирует основную асинхронную функцию `main` из модуля `src.bot.main`
# и запускает ее с помощью `asyncio.run()`.

if __name__ == "__main__":
    # Этот блок выполняется только при запуске скрипта напрямую.
    # asyncio.run() создает новый цикл событий и запускает в нем
    # корутину `run_bot()` до ее завершения.
    asyncio.run(run_bot())
