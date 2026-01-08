"""
Модуль обработки данных для RAG системы.

Содержит скрипты для:
- Скачивания HTML из Яндекс Хендбуков
- Извлечения текста и создания чанков
- Построения FAISS индекса
"""

from pathlib import Path

# Корень проекта (2 уровня вверх от этого файла)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Стандартные пути к данным
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw" / "handbook"
PROCESSED_DATA_DIR = DATA_DIR / "handbook"
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"

