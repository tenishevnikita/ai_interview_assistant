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
    max_doc_chars = max_chars // 5
    target_doc_count = min(len(docs), 6)
    avg_chars_per_doc = (max_chars - 200) // target_doc_count
    
    for i, d in enumerate(docs, start=1):
        meta = d.metadata or {}
        title = meta.get("title") or meta.get("source") or meta.get("chunk_id") or f"doc_{i}"
        snippet = (d.page_content or "").strip()
        if snippet.startswith("passage: "):
            snippet = snippet[9:]
        if not snippet:
            continue
        
        header_len = len(f"[{i}] {title}\n\n")
        available_space = max_chars - total - header_len - 50
        
        if available_space <= 0:
            break
        
        max_snippet_len = min(available_space, max_doc_chars, avg_chars_per_doc)
        if i <= target_doc_count and available_space > 1000:
            max_snippet_len = max(max_snippet_len, min(1000, available_space))
        
        if len(snippet) > max_snippet_len:
            truncated = snippet[:max_snippet_len]
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")
            cut_point = max(last_period, last_newline)
            if cut_point > max_snippet_len * 0.7:
                snippet = truncated[:cut_point + 1] + "..."
            else:
                snippet = truncated + "..."
        
        block = f"[{i}] {title}\n{snippet}\n"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts).strip()


async def _retry_with_backoff(func, max_retries: int = 3, initial_delay: float = 1.0):
    """Retry with exponential backoff on rate limit errors."""
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = (
                "429" in error_str
                or "rate limit" in error_str
                or "too many requests" in error_str
            )

            if is_rate_limit and attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logger.warning(f"Rate limit (attempt {attempt + 1}/{max_retries}), retry in {delay:.1f}s")
                await asyncio.sleep(delay)
                last_exception = e
                continue
            else:
                raise

    if last_exception:
        raise last_exception


def _format_sources(docs: list[Document]) -> str:
    """Formats document sources as Telegram HTML links."""
    if not docs:
        return ""

    sources: list[str] = []
    seen_combinations: set[tuple[str, str]] = set()

    for doc in docs:
        meta = doc.metadata or {}
        title = meta.get("title")
        source_link = meta.get("source_link", "")
        
        if not title or not source_link:
            content = doc.page_content or ""
            if content.startswith("passage: "):
                content = content[9:]
            
            if not source_link:
                match = re.search(r"\[source_link:\s*([^\]]+)\]", content)
                if match:
                    source_link = match.group(1).strip()
            
            if not title:
                lines = content.split("\n")
                for line in lines[:15]:
                    stripped = line.strip()
                    if stripped.startswith("# ") and not stripped.startswith("## "):
                        title = stripped.removeprefix("# ").strip()
                        break
        
        if not title:
            title = meta.get("source") or meta.get("chunk_id")

        if not title:
            continue

        key = (title, source_link)
        if key in seen_combinations:
            continue
        seen_combinations.add(key)

        escaped_text = html.escape(title)
        if source_link:
            source_item = f"• <a href=\"{html.escape(source_link)}\">{escaped_text}</a>"
        else:
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
        """Returns final answer."""
        answer, _, _, _ = await self.answer_with_details(chat_id, user_id, user_text)
        return answer

    async def answer_with_details(
        self, chat_id: int, user_id: int, user_text: str
    ) -> tuple[str, str, list[Document], str]:
        """Returns answer with intermediate data: (answer, standalone_question, docs, context)."""
        history = self._memory.get_history_messages(chat_id=chat_id)
        prefs = self._memory.get_prefs(user_id=user_id)

        async def rewrite_question():
            return await self._rewrite_chain.ainvoke({"history": history, "input": user_text})

        try:
            standalone_q = await _retry_with_backoff(rewrite_question)
            standalone_q = (standalone_q or "").strip() or user_text
        except Exception as e:
            logger.error(f"Rewrite error: {e}", exc_info=True)
            standalone_q = user_text

        docs: list[Document] = []
        try:
            docs = self._retriever.retrieve(standalone_q, k=settings.retrieval_k)
        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)

        context = _format_docs(docs)
        disclaimer = ""
        if not context:
            if isinstance(self._retriever, EmptyRetriever):
                disclaimer = "Примечание: база знаний не подключена. Ответ ниже — общий (может быть неточным).\n\n"
            else:
                disclaimer = "Примечание: в базе знаний не найдено релевантной информации по вашему запросу. Ответ ниже — общий (может быть неточным).\n\n"
            context = "(контекст пуст)"

        async def generate_answer():
            return await self._answer_chain.ainvoke(
                {"question": standalone_q, "context": context, "style": prefs.style.value}
            )

        try:
            answer = await _retry_with_backoff(generate_answer)
            answer = (answer or "").strip()
        except Exception as e:
            logger.error(f"Answer generation error: {e}", exc_info=True)
            answer = "Не смог сформировать ответ. Попробуй задать вопрос иначе."

        if not answer:
            answer = "Не смог сформировать ответ. Попробуй задать вопрос иначе."

        answer = f"{disclaimer}{answer}".strip()

        answer_lower = answer.lower()
        no_info_phrases = [
            "в базе нет информации",
            "в базе знаний не найдено",
            "не найдено релевантной информации",
            "не содержит нужной информации",
            "нет ответа на вопрос",
            "нет данных по запросу",
            "не могу ответить",
            "не смог найти информацию",
        ]
        has_no_info = False
        for phrase in no_info_phrases:
            if phrase in answer_lower:
                idx = answer_lower.find(phrase)
                context_start = max(0, idx - 50)
                context_end = min(len(answer_lower), idx + len(phrase) + 50)
                context = answer_lower[context_start:context_end]
                conditional_words = ["если", "когда", "в случае", "при отсутствии"]
                is_conditional = any(word in context[:idx - context_start] for word in conditional_words)
                if not is_conditional:
                    has_no_info = True
                    break

        if docs and not disclaimer and not has_no_info:
            sources = _format_sources(docs)
            if sources:
                answer = f"{answer}{sources}"

        self._memory.append_user(chat_id=chat_id, text=user_text)
        self._memory.append_ai(chat_id=chat_id, text=answer)
        
        return answer, standalone_q, docs, context
