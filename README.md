# UTMN News Scraper

Гибридная асинхронно-параллельная система сбора и доставки новостей с сайта [https://www.utmn.ru/news](https://www.utmn.ru/news) с использованием Telegram-бота.

## Особенности

-   **Асинхронный скрейпинг**: Загружает страницы новостей асинхронно с использованием `aiohttp`.
-   **Параллельный парсинг**: Обрабатывает HTML в параллельном режиме, используя `multiprocessing`.
-   **Telegram-бот**: Взаимодействует с пользователями для предоставления новостей по их запросам.
-   **Бенчмаркинг**: Скрипты для измерения и сравнения производительности различных методов скрейпинга.
-   **Поддержка Docker**: для воспроизводимости экспериментов.

## Структура проекта

```
.
├── README.md
├── LICENSE
├── pyproject.toml
├── config.yaml
├── src/
│   ├── bot/
│   │   ├── main.py
│   │   ├── commands.py
│   │   └── utils.py
│   ├── scraper/
│   │   ├── async_fetcher.py
│   │   ├── queue_manager.py
│   │   ├── parser.py
│   │   ├── storage.py
│   │   └── cache.py
│   ├── bench/
│   │   ├── runner.py
│   │   └── plot_results.py
│   ├── tests/
│   └── utils/
│       ├── logging.py
│       ├── timing.py
│       └── monitoring.py
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── report/
│   ├── template.md
│   └── template.tex
└── scripts/
    ├── run_scraper.py
    ├── run_bot.py
    ├── run_bench.sh
    └── init_db.py
```

## Установка

1.  **Клонируйте репозиторий:**
    ```bash
    git clone https://github.com/webmasha/utmn-news-parallel-scraper.git
    ```
2.  **Создайте и активируйте виртуальное окружение:**
    ```bash
    uv init    
    uv venv --seed
    ```
3.  **Установите uv и зависимости:**
    ```bash  
    uv pip install .  
    ```

## Конфигурация

1.  Скопируйте `config.yaml` в `config.local.yaml` и отредактируйте его.
2.  Установите ваш `telegram_token` в `config.local.yaml`. Вы можете получить токен, поговорив с [@BotFather](https://t.me/BotFather) в Telegram.
3.  В качестве альтернативы, вы можете установить переменную окружения `TELEGRAM_TOKEN`.

## Использование

Для всех команд ниже предполагается, что вы активировали виртуальное окружение (`source .venv/bin/activate`).

1.  **Инициализируйте базу данных:**
    ```bash
    uv run python $(pwd)/scripts/init_db.py
    ```

2.  **Запустите скрейпер:**
    ```bash
    uv run python $(pwd)/scripts/run_scraper.py
    ```

3.  **Запустите Telegram-бота:**
    ```bash
    uv run python $(pwd)/scripts/run_bot.py
    ```
4. **Запустите линтеры и тесты**
   ```bash
   pytest
   ```

## Команды бота

-   `/start` - Запустить бота
-   `/help` - Показать справочное сообщение
-   `/news [категория] [дата_начала] [дата_окончания]` - Получить новости для определенной категории и/или диапазона дат.
    -   Пример: `/news` - получить все новости
    -   Пример: `/news science` - получить новости из категории "наука"
    -   Пример: `/news 01.01.2024 31.01.2024` - получить новости за определенный диапазон дат
    -   Пример: `/news science 01.01.2024 31.01.2024` - получить новости из категории "наука" за определенный диапазон дат

## Бенчмаркинг

Чтобы запустить тесты производительности и сравнить производительность различных методов скрейпинга, выполните следующую команду:
```bash
bash scripts/run_bench.sh
```
Результаты будут сохранены в каталоге `bench/results`.

Чтобы построить график результатов, выполните:
```bash
uv run python $(pwd)/src/bench/plot_results.py
```

## Docker

Чтобы запустить приложение с помощью Docker, сначала создайте образ:
```bash
docker-compose build
```
Затем запустите сервисы:
```bash
docker-compose up -d
```
Это запустит телеграм-бота.
Чтобы запустить скрейпер, вы можете выполнить команду внутри контейнера:
```bash
docker-compose exec app python scripts/run_scraper.py
```

## Участие в разработке

Pull request-ы приветствуются. Для серьезных изменений, пожалуйста, сначала откройте issue, чтобы обсудить, что вы хотели бы изменить.

Пожалуйста, убедитесь, что вы обновляете тесты соответствующим образом.

## Лицензия

[MIT](https://choosealicense.com/licenses/mit/)