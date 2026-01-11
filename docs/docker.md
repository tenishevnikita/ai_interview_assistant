# Docker Setup

## Обзор

Проект поддерживает запуск через Docker Compose, что упрощает развертывание и обеспечивает автоматическую инициализацию данных.

## Структура

- **Dockerfile** — образ приложения с Python 3.12 и всеми зависимостями
- **docker-compose.yaml** — конфигурация сервисов:
  - `data-init` — сервис инициализации данных (обновление чанков и пересборка индекса)
  - `bot` — телеграм бот

## Быстрый старт

1. Создай `.env` файл:

```bash
cp env.example .env
```

2. Заполни необходимые переменные в `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `MISTRAL_API_KEY`
   - `ADMIN_USER_IDS` (опционально)

3. Запусти:

```bash
docker-compose up --build
```

## Сервисы

### data-init

Сервис для инициализации данных. Выполняет:
- Извлечение чанков из всех handbook'ов:
  - Python (`extract_handbook`)
  - ML (`extract_handbook_ml`)
  - CS (`extract_handbook_cs`)
  - C++ (`extract_handbook_cpp`)
  - Algorithms (`extract_handbook_algo`)
  - Linux (`extract_handbook_linux`)
  - Math (`extract_handbook_math`)
- Построение FAISS индекса (`build_index`)

**Логика работы:**
- Запускается автоматически при старте `bot`
- Проверяет наличие индекса в `/app/data/faiss_index/index.faiss`
- Если индекс отсутствует → обновляет чанки и пересобирает индекс
- Если индекс существует → пропускает инициализацию

**Принудительная пересборка:**

```bash
FORCE_REBUILD_INDEX=true docker-compose up --build
```

### bot

Телеграм бот. Запускается после успешной инициализации данных.

**Зависимости:**
- Ждет завершения `data-init` (через `depends_on` с `condition: service_completed_successfully`)
- Автоматически перезапускается при сбоях (`restart: unless-stopped`)

## Volumes

- `./data:/app/data` — данные проекта (handbook'и, чанки, индекс)
- `./.env:/app/.env:ro` — переменные окружения (read-only)

## Переменные окружения

### data-init

- `PYTHONPATH=/app` — путь для импорта модулей
- `FORCE_REBUILD_INDEX` — принудительная пересборка индекса (по умолчанию: `false`)

### bot

Все переменные из `.env` файла автоматически загружаются через `env_file`.

## Команды

### Первый запуск

```bash
docker-compose up --build
```

### Обычный запуск

```bash
docker-compose up
```

### Запуск в фоне

```bash
docker-compose up -d
```

### Остановка

```bash
docker-compose down
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Только бот
docker-compose logs -f bot

# Только инициализация
docker-compose logs -f data-init
```

### Пересборка образа

```bash
docker-compose build --no-cache
```

### Принудительная пересборка индекса

```bash
FORCE_REBUILD_INDEX=true docker-compose up --build
```

## Troubleshooting

### Индекс не создается

Проверь логи инициализации:

```bash
docker-compose logs data-init
```

Убедись, что:
- HTML файлы присутствуют в `data/raw/handbook/`
- Скрипты извлечения успешно завершились
- Достаточно места на диске

### Бот не запускается

Проверь:
- Наличие `.env` файла с корректными токенами
- Логи бота: `docker-compose logs bot`
- Что `data-init` успешно завершился

### Очистка данных

Для полной пересборки с нуля:

```bash
# Останови контейнеры
docker-compose down

# Удали данные (опционально)
rm -rf data/faiss_index data/handbook

# Запусти заново
FORCE_REBUILD_INDEX=true docker-compose up --build
```

## Оптимизация

### Кэширование слоев

Dockerfile оптимизирован для кэширования:
1. Системные зависимости
2. Установка `uv`
3. Копирование `pyproject.toml` и `uv.lock`
4. Установка Python зависимостей
5. Копирование исходного кода

При изменении только кода пересборка будет быстрой.

### .dockerignore

Файл `.dockerignore` исключает из образа:
- `__pycache__/`, `.venv/` — кэши Python
- `data/` — данные (монтируются как volume)
- `.git/`, `.vscode/` — служебные файлы
- `tests/`, `docs/` — не нужны в образе

Это ускоряет сборку и уменьшает размер образа.

