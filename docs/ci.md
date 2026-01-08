# CI/CD Configuration

## Настройка

В проекте настроен GitHub Actions CI, который автоматически запускается при:
- Push в ветки `main`, `master`, `develop`
- Pull Request в эти же ветки

## Что проверяет CI

1. **Линтинг с ruff**
   - Проверка стиля кода
   - Сортировка импортов
   - Соответствие PEP 8

2. **Форматирование с ruff**
   - Проверка форматирования кода

3. **Тесты**
   - Unit-тесты (без сетевых запросов)
   - E2E тесты (только если настроен `MISTRAL_API_KEY` в Secrets)

## Локальная проверка

### Быстрая проверка всего

```bash
make check
```

### Отдельные команды

Линтинг:
```bash
make lint
# или
uv run ruff check .
```

Форматирование:
```bash
make format
# или
uv run ruff format .
```

Тесты:
```bash
make test
# или
uv run pytest tests/ --ignore=tests/e2e
```

## Pre-commit хуки

Для автоматической проверки перед каждым коммитом:

```bash
# Установить dev-зависимости
uv sync --all-groups

# Установить хуки
uv run pre-commit install

# Теперь при каждом коммите будут автоматически запускаться:
# - ruff check --fix
# - ruff format
# - trailing-whitespace
# - end-of-file-fixer
# - check-yaml
# - check-added-large-files
# - check-merge-conflict
```

Запустить хуки вручную на всех файлах:
```bash
uv run pre-commit run --all-files
```

## Настройка Secrets в GitHub

Для запуска E2E тестов в CI нужно добавить секреты:

1. Перейти в Settings → Secrets and variables → Actions
2. Добавить `MISTRAL_API_KEY` с вашим API ключом

## Конфигурация ruff

Настройки в `pyproject.toml`:
- Длина строки: 120 символов
- Python версия: 3.12
- Проверки: pycodestyle, Pyflakes, isort, pep8-naming, black
- Игнорируются: uppercase для переменных типа `X_train`, длинные строки

## Решение проблем

### CI падает на ruff check

```bash
# Локально исправить автоматически
uv run ruff check --fix .
uv run ruff format .
```

### CI падает на тестах

```bash
# Запустить тесты локально
uv run pytest tests/ -v
```

### Pre-commit хуки слишком строгие

Можно временно пропустить хуки:
```bash
git commit --no-verify -m "message"
```

Но лучше исправить код согласно линтеру.

