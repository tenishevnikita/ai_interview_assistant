from __future__ import annotations

import asyncio
import html
import logging
import re
from dataclasses import dataclass
from typing import Protocol

from langchain_core.documents import Document
from langchain_mistralai import ChatMistralAI

from src.config import settings
from src.llm.chains import build_answer_chain, build_rewrite_chain
from src.llm.memory import MemoryStore

logger = logging.getLogger(__name__)


class Retriever(Protocol):
    def retrieve(self, question: str, k: int = 5) -> list[Document]: ...


@dataclass(frozen=True)
class EmptyRetriever:
    def retrieve(self, question: str, k: int = 5) -> list[Document]:
        return []


def _format_docs(docs: list[Document], max_chars: int = 6000) -> str:
    if not docs:
        return ""

    parts: list[str] = []
    total = 0
    for i, d in enumerate(docs, start=1):
        meta = d.metadata or {}
        title = meta.get("title") or meta.get("source") or meta.get("chunk_id") or f"doc_{i}"
        snippet = (d.page_content or "").strip()
        # Убираем префикс "passage: " который добавляется для e5 моделей
        if snippet.startswith("passage: "):
            snippet = snippet[9:]
        if not snippet:
            continue
        block = f"[{i}] {title}\n{snippet}\n"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts).strip()


async def _retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    """
    Выполняет функцию с повторными попытками при ошибке 429 (rate limit).

    Args:
        func: асинхронная функция для выполнения
        max_retries: максимальное количество попыток
        initial_delay: начальная задержка в секундах (удваивается при каждой попытке)

    Returns:
        результат выполнения функции

    Raises:
        последнее исключение, если все попытки исчерпаны
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            # Проверяем, является ли это ошибкой rate limit (429)
            error_str = str(e).lower()
            is_rate_limit = (
                "429" in error_str
                or "rate limit" in error_str
                or "too many requests" in error_str
            )

            if is_rate_limit and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.warning(
                    f"Rate limit ошибка (попытка {attempt + 1}/{max_retries}). "
                    f"Повтор через {delay:.1f} сек..."
                )
                await asyncio.sleep(delay)
                last_exception = e
                continue
            else:
                # Если это не rate limit или попытки закончились - пробрасываем ошибку
                raise

    # Если все попытки исчерпаны
    if last_exception:
        raise last_exception


def _format_sources(docs: list[Document]) -> str:
    """
    Форматирует список источников из документов для отображения в ответе.
    Создает кликабельные ссылки в формате Telegram HTML.
    Извлекает source_link и title из page_content, если их нет в metadata.

    Args:
        docs: список документов с metadata и page_content

    Returns:
        отформатированная строка с источниками или пустая строка
    """
    if not docs:
        return ""

    sources: list[str] = []
    seen_combinations: set[tuple[str, str]] = set()  # (title, source_link) для дедупликации

    for doc in docs:
        meta = doc.metadata or {}
        
        # Сначала пытаемся взять из metadata
        title = meta.get("title")
        source_link = meta.get("source_link", "")
        
        # Если нет в metadata, извлекаем из page_content
        if not title or not source_link:
            content = doc.page_content or ""
            # Убираем префикс "passage: " если есть
            if content.startswith("passage: "):
                content = content[9:]
            
            # Извлекаем source_link из начала чанка (формат: [source_link: URL])
            if not source_link:
                match = re.search(r"\[source_link:\s*([^\]]+)\]", content)
                if match:
                    source_link = match.group(1).strip()
            
            # Извлекаем title из строки с # (название статьи, не ##)
            if not title:
                lines = content.split("\n")
                for line in lines[:15]:  # Проверяем первые 15 строк
                    stripped = line.strip()
                    if stripped.startswith("# ") and not stripped.startswith("## "):
                        title = stripped.removeprefix("# ").strip()
                        break
        
        # Fallback на другие поля metadata
        if not title:
            title = meta.get("source") or meta.get("chunk_id")

        if not title:
            continue

        # Дедупликация по комбинации title + source_link
        key = (title, source_link)
        if key in seen_combinations:
            continue
        seen_combinations.add(key)

        # Экранируем HTML в тексте ссылки
        escaped_text = html.escape(title)

        # Формируем источник
        if source_link:
            # Создаем кликабельную ссылку в формате Telegram HTML
            source_item = f"• <a href=\"{html.escape(source_link)}\">{escaped_text}</a>"
        else:
            # Если нет ссылки, просто текст
            source_item = f"• {escaped_text}"

        sources.append(source_item)

    if not sources:
        return ""

    return "\n\n📚 Источники:\n" + "\n".join(sources)


class RAGEngine:
    def __init__(self, memory: MemoryStore, retriever: Retriever | None = None) -> None:
        self._memory = memory
        self._retriever = retriever or EmptyRetriever()

        self._model = ChatMistralAI(
            api_key=settings.mistral_api_key,
            model="mistral-small-latest",
            temperature=0.2,
        )
        self._rewrite_chain = build_rewrite_chain(self._model)
        self._answer_chain = build_answer_chain(self._model)

    async def answer(self, chat_id: int, user_id: int, user_text: str) -> str:
        history = self._memory.get_history_messages(chat_id=chat_id)
        prefs = self._memory.get_prefs(user_id=user_id)

        # Rewrite с retry
        async def rewrite_question():
            return await self._rewrite_chain.ainvoke({"history": history, "input": user_text})

        try:
            standalone_q = await _retry_with_backoff(rewrite_question)
            standalone_q = (standalone_q or "").strip() or user_text
        except Exception as e:
            logger.error(f"Ошибка при переписывании вопроса: {e}", exc_info=True)
            standalone_q = user_text

        # Получение документов из ретривера с обработкой ошибок
        docs: list[Document] = []
        try:
            docs = self._retriever.retrieve(standalone_q, k=5)
        except Exception as e:
            logger.error(f"Ошибка при поиске документов: {e}", exc_info=True)

        context = _format_docs(docs)
        disclaimer = ""
        if not context:
            if isinstance(self._retriever, EmptyRetriever):
                disclaimer = (
                    "Примечание: база знаний не подключена. "
                    "Ответ ниже — общий (может быть неточным).\n\n"
                )
            else:
                disclaimer = (
                    "Примечание: в базе знаний не найдено релевантной информации по вашему запросу. "
                    "Ответ ниже — общий (может быть неточным).\n\n"
                )
            context = "(контекст пуст)"

        # Answer с retry
        async def generate_answer():
            return await self._answer_chain.ainvoke(
                {"question": standalone_q, "context": context, "style": prefs.style.value}
            )

        try:
            answer = await _retry_with_backoff(generate_answer)
            answer = (answer or "").strip()
        except Exception as e:
            logger.error(f"Ошибка при генерации ответа: {e}", exc_info=True)
            answer = "Не смог сформировать ответ. Попробуй задать вопрос иначе."

        if not answer:
            answer = "Не смог сформировать ответ. Попробуй задать вопрос иначе."

        # Добавляем disclaimer в начало
        answer = f"{disclaimer}{answer}".strip()

        # Проверяем, говорит ли ответ о том, что информации нет в базе
        # Если да - не показываем источники, даже если они есть
        answer_lower = answer.lower()
        no_info_phrases = [
            "в базе нет информации",
            "нет информации",
            "не найдено",
            "не содержит",
            "нет ответа",
            "нет данных",
        ]
        has_no_info = any(phrase in answer_lower for phrase in no_info_phrases)

        # Добавляем ссылки на источники только если:
        # 1. Есть документы
        # 2. Нет disclaimer о пустой базе
        # 3. Ответ не говорит о том, что информации нет
        if docs and not disclaimer and not has_no_info:
            sources = _format_sources(docs)
            if sources:
                answer = f"{answer}{sources}"

        self._memory.append_user(chat_id=chat_id, text=user_text)
        self._memory.append_ai(chat_id=chat_id, text=answer)
        return answer
