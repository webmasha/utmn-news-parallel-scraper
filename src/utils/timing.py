import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

def timeit(func: Callable) -> Callable:
    """
    Декоратор для измерения времени выполнения асинхронной функции.

    Оборачивает асинхронную функцию, замеряет время от начала до конца
    ее выполнения и логирует результат.

    Args:
        func: Асинхронная функция для измерения.

    Returns:
        Обновленная асинхронная функция-обертка.
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logger.info(f"Функция {func.__name__} выполнилась за {total_time:.4f} секунд")
        return result
    return wrapper

def timeit_sync(func: Callable) -> Callable:
    """
    Декоратор для измерения времени выполнения синхронной функции.

    Оборачивает синхронную функцию, замеряет время от начала до конца
    ее выполнения и логирует результат.

    Args:
        func: Синхронная функция для измерения.

    Returns:
        Обновленная синхронная функция-обертка.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logger.info(f"Функция {func.__name__} выполнилась за {total_time:.4f} секунд")
        return result
    return wrapper
