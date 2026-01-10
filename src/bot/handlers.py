from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.bot.admin import save_uploaded_file, validate_file
from src.bot.formatting import format_and_split_for_telegram_html
from src.config import settings
from src.llm.memory import MemoryStore, Style
from src.llm.rag_engine import RAGEngine
from src.vector_store import create_retriever

logger = logging.getLogger(__name__)

router = Router(name=__name__)

memory = MemoryStore()

# Инициализация ретривера
try:
    retriever = create_retriever()
    if retriever.is_ready:
        logger.info(f"✓ FAISS индекс загружен. Документов: {retriever.document_count}")
    else:
        logger.warning("⚠️ FAISS индекс не найден или пуст. Бот будет работать без базы знаний.")
except Exception as e:
    logger.error(f"❌ Ошибка при загрузке ретривера: {e}")
    retriever = None

engine = RAGEngine(memory=memory, retriever=retriever)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    text = (
        "Привет! Я ассистент для подготовки к собеседованиям.\n\n"
        "Как пользоваться:\n"
        "- Просто задай вопрос текстом.\n"
        "- Если хочешь уточнить: «расскажи подробнее про 3-й пункт» — я учту контекст.\n\n"
        "Стили ответа:\n"
        "- /brief — кратко\n"
        "- /detailed — подробно + пример\n"
    )
    for chunk in format_and_split_for_telegram_html(text):
        await message.answer(chunk)


@router.message(Command("brief"))
async def cmd_brief(message: Message) -> None:
    if not message.from_user:
        return
    memory.set_style(user_id=message.from_user.id, style=Style.BRIEF)
    await message.answer("Ок. Буду отвечать кратко.")


@router.message(Command("detailed"))
async def cmd_detailed(message: Message) -> None:
    if not message.from_user:
        return
    memory.set_style(user_id=message.from_user.id, style=Style.DETAILED)
    await message.answer("Ок. Буду отвечать подробно и добавлять примеры.")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Команда помощи."""
    text = (
        "📖 Помощь\n\n"
        "Как пользоваться:\n"
        "- Просто задай вопрос текстом.\n"
        "- Если хочешь уточнить: «расскажи подробнее про 3-й пункт» — я учту контекст.\n\n"
        "Стили ответа:\n"
        "- /brief — кратко\n"
        "- /detailed — подробно + пример\n\n"
        "Другие команды:\n"
        "- /start — начать работу с ботом\n"
        "- /clear — очистить контекст диалога\n"
        "- /help — показать эту справку"
    )
    for chunk in format_and_split_for_telegram_html(text):
        await message.answer(chunk)


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    """Очищает контекст диалога."""
    if not message.from_user or not message.chat:
        return

    chat_id = message.chat.id
    memory.clear_history(chat_id)
    await message.answer("✅ Контекст диалога очищен. Можете начать новый диалог.")


def _is_admin(user_id: int | None) -> bool:
    """Проверяет, является ли пользователь администратором."""
    if user_id is None:
        return False
    return user_id in settings.admin_user_ids_list


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """Команда для доступа к админ-функциям."""
    if not message.from_user:
        return

    if not _is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return

    text = (
        "🔧 Админ-панель\n\n"
        "Доступные функции:\n"
        "- Отправьте PDF файл для добавления в базу знаний"
    )
    await message.answer(text)


@router.message(lambda m: m.document is not None)
async def on_document(message: Message) -> None:
    """Обработчик загрузки документов."""
    if not message.from_user or not message.document:
        return

    # Проверка прав администратора
    if not _is_admin(message.from_user.id):
        await message.answer("❌ Только администраторы могут загружать файлы.")
        return

    doc = message.document
    file_size = doc.file_size or 0

    # Валидация файла
    file_path = Path(doc.file_name or "unknown")
    is_valid, error_msg = validate_file(file_path, file_size)

    if not is_valid:
        await message.answer(f"❌ {error_msg}")
        return

    try:
        # Скачивание файла
        # В aiogram 3.x bot.download() возвращает BytesIO напрямую
        bot = message.bot
        file_bytes_io = await bot.download(doc.file_id)

        if file_bytes_io is None:
            await message.answer("❌ Не удалось скачать файл.")
            return

        # Читаем содержимое файла из BytesIO (синхронный метод, без await)
        file_bytes_io.seek(0)  # Убеждаемся, что указатель в начале
        file_bytes = file_bytes_io.read()

        # Сохранение файла
        saved_path = save_uploaded_file(
            file_bytes,
            doc.file_name or "unknown",
            settings.temp_files_dir,
        )

        await message.answer(
            f"✅ Файл сохранен: {saved_path.name}\n\n"
            "Примечание: основная логика парсинга и добавления в индекс будет реализована позже."
        )
        logger.info(f"Админ {message.from_user.id} загрузил файл: {saved_path}")

    except Exception as e:
        logger.error(f"Ошибка при обработке документа: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка при обработке файла: {e}")


@router.message()
async def on_text(message: Message) -> None:
    if not message.text:
        return

    chat_id = message.chat.id
    if not message.from_user:
        return
    user_id = message.from_user.id
    user_text = message.text.strip()
    if not user_text:
        return

    answer = await engine.answer(chat_id=chat_id, user_id=user_id, user_text=user_text)
    for chunk in format_and_split_for_telegram_html(answer):
        await message.answer(chunk)
