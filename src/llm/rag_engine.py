from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from langchain_core.documents import Document
from langchain_mistralai import ChatMistralAI

from src.config import settings
from src.llm.chains import build_answer_chain, build_rewrite_chain
from src.llm.memory import MemoryStore


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
        if not snippet:
            continue
        block = f"[{i}] {title}\n{snippet}\n"
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block)
    return "\n".join(parts).strip()


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

        standalone_q = await self._rewrite_chain.ainvoke({"history": history, "input": user_text})
        standalone_q = (standalone_q or "").strip() or user_text

        docs = self._retriever.retrieve(standalone_q, k=5)
        context = _format_docs(docs)
        disclaimer = ""
        if not context:
            disclaimer = (
                "Примечание: база знаний пока пустая или индекс не подключён. "
                "Ответ ниже — общий (может быть неточным).\n\n"
            )
            context = "(контекст пуст)"

        answer = await self._answer_chain.ainvoke(
            {"question": standalone_q, "context": context, "style": prefs.style.value}
        )
        answer = (answer or "").strip()
        if not answer:
            answer = "Не смог сформировать ответ. Попробуй задать вопрос иначе."

        answer = f"{disclaimer}{answer}".strip()

        self._memory.append_user(chat_id=chat_id, text=user_text)
        self._memory.append_ai(chat_id=chat_id, text=answer)
        return answer


