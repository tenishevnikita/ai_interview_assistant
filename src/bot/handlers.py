from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.bot.formatting import format_and_split_for_telegram_html
from src.llm.memory import MemoryStore, Style
from src.llm.rag_engine import RAGEngine

router = Router(name=__name__)

memory = MemoryStore()
engine = RAGEngine(memory=memory)


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
        "- /socratic — наводящие вопросы + ответ\n"
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


@router.message(Command("socratic"))
async def cmd_socratic(message: Message) -> None:
    if not message.from_user:
        return
    memory.set_style(user_id=message.from_user.id, style=Style.SOCRATIC)
    await message.answer("Ок. Буду задавать 1–3 наводящих вопроса и затем отвечать.")


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
