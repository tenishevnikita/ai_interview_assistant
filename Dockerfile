FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Установка uv
RUN pip install --no-cache-dir uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock ./

# Установка зависимостей
RUN uv sync --frozen --no-dev

# Копирование исходного кода
COPY . .

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

# Команда по умолчанию (переопределяется в docker-compose)
CMD ["python", "-m", "src.bot.main"]

