#!/bin/bash

# Этот скрипт запускает бенчмарки и затем генерирует графики.

# Убедимся, что мы находимся в директории скрипта
cd "$(dirname "$0")/.."

# Активируем виртуальное окружение
source .venv/bin/activate

# Проверяем, установлен ли uv (для генерации requirements.txt)
if ! command -v uv &> /dev/null
then
    echo "Утилита uv не найдена. Пожалуйста, установите ее."
    exit
fi

echo "Запуск бенчмарка..."
python src/bench/runner.py

echo "Генерация графиков результатов..."
python src/bench/plot_results.py

echo "Бенчмарк завершен. Результаты находятся в директории src/bench/results."
