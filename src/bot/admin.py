"""Админ-функции для бота: загрузка и валидация документов."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Максимальный размер файла в байтах (Telegram ограничивает до 20MB для ботов)
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

# Поддерживаемые форматы файлов
SUPPORTED_FORMATS = {".pdf"}


def validate_file(file_path: Path, file_size: int) -> tuple[bool, str]:
    """
    Валидирует загруженный файл.

    Args:
        file_path: путь к файлу
        file_size: размер файла в байтах

    Returns:
        (is_valid, error_message)
    """
    # Проверка расширения файла
    if file_path.suffix.lower() not in SUPPORTED_FORMATS:
        return False, f"Неподдерживаемый формат файла. Поддерживаются: {', '.join(SUPPORTED_FORMATS)}"

    # Проверка размера файла
    if file_size > MAX_FILE_SIZE:
        return False, f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE / (1024 * 1024):.0f} MB"

    return True, ""


def save_uploaded_file(file_content: bytes, filename: str, temp_dir: Path) -> Path:
    """
    Сохраняет загруженный файл во временную директорию.

    Args:
        file_content: содержимое файла
        filename: имя файла
        temp_dir: директория для временных файлов

    Returns:
        путь к сохраненному файлу
    """
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Создаем безопасное имя файла
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")[:100]
    file_path = temp_dir / safe_filename

    # Если файл с таким именем уже существует, добавляем суффикс
    counter = 1
    while file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        file_path = temp_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    file_path.write_bytes(file_content)
    logger.info(f"Файл сохранен: {file_path}")

    return file_path
