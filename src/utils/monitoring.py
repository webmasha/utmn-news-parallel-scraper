import os
import psutil
import logging

logger = logging.getLogger(__name__)

def get_resource_usage():
    """
    Возвращает текущее использование CPU и оперативной памяти процессом.

    Использует библиотеку `psutil` для получения информации о текущем процессе.

    Returns:
        Словарь, содержащий:
        - `cpu_percent`: процент загрузки CPU текущим процессом.
        - `memory_mb`: объем используемой оперативной памяти (RSS) в мегабайтах.
    """
    process = psutil.Process(os.getpid())
    
    # Использование CPU
    # interval=1 означает, что будет измерена загрузка за последнюю секунду
    cpu_usage = process.cpu_percent(interval=1)
    
    # Использование памяти
    mem_info = process.memory_info()
    rss_mb = mem_info.rss / (1024 * 1024)  # Resident Set Size в МБ
    
    return {"cpu_percent": cpu_usage, "memory_mb": rss_mb}

def log_resource_usage():
    """
    Логирует текущее использование ресурсов.

    Вызывает `get_resource_usage` и выводит результат в лог
    на уровне INFO.
    """
    usage = get_resource_usage()
    logger.info(f"Использование ресурсов: CPU={usage['cpu_percent']:.2f}%, Память={usage['memory_mb']:.2f} МБ")
