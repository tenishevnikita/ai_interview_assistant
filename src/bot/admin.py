"""Admin functions for bot: file upload and validation."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024
SUPPORTED_FORMATS = {".pdf"}


def validate_file(file_path: Path, file_size: int) -> tuple[bool, str]:
    if file_path.suffix.lower() not in SUPPORTED_FORMATS:
        return (
            False,
            f"Неподдерживаемый формат файла. Поддерживаются: {', '.join(SUPPORTED_FORMATS)}",
        )

    if file_size > MAX_FILE_SIZE:
        return (
            False,
            f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE / (1024 * 1024):.0f} MB",
        )

    return True, ""


def save_uploaded_file(file_content: bytes, filename: str, temp_dir: Path) -> Path:
    temp_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = "".join(c for c in filename if c.isalnum() or c in ".-_")[:100]
    file_path = temp_dir / safe_filename

    counter = 1
    while file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        file_path = temp_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    file_path.write_bytes(file_content)
    logger.info(f"Файл сохранен: {file_path}")

    return file_path
