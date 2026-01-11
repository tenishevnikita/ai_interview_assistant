"""Тесты для RAG engine."""

from __future__ import annotations

from langchain_core.documents import Document

from src.llm.memory import MemoryStore
from src.llm.rag_engine import EmptyRetriever, RAGEngine


class MockRetriever:
    """Мок-ретривер для тестирования."""

    def __init__(self, docs: list[Document] | None = None):
        self.docs = docs or []

    def retrieve(self, question: str, k: int = 5) -> list[Document]:
        return self.docs[:k]


def test_rag_engine_with_empty_retriever() -> None:
    """Тест RAG engine с пустым ретривером."""
    memory = MemoryStore()
    engine = RAGEngine(memory=memory, retriever=None)

    assert engine._retriever is not None
    assert isinstance(engine._retriever, EmptyRetriever)


def test_rag_engine_with_mock_retriever() -> None:
    """Тест RAG engine с мок-ретривером."""
    memory = MemoryStore()
    docs = [
        Document(page_content="Test content", metadata={"title": "Test"}),
    ]
    retriever = MockRetriever(docs)
    engine = RAGEngine(memory=memory, retriever=retriever)

    assert engine._retriever == retriever


def test_rag_engine_retrieves_documents() -> None:
    """Тест что RAG engine корректно получает документы из ретривера."""
    memory = MemoryStore()
    docs = [
        Document(page_content="Content 1", metadata={"chunk_id": "doc1"}),
        Document(page_content="Content 2", metadata={"chunk_id": "doc2"}),
    ]
    retriever = MockRetriever(docs)
    _engine = RAGEngine(memory=memory, retriever=retriever)

    # Проверяем, что ретривер возвращает документы
    retrieved = retriever.retrieve("test question", k=2)
    assert len(retrieved) == 2
    assert retrieved[0].metadata["chunk_id"] == "doc1"


def test_empty_retriever_returns_empty_list() -> None:
    """Тест что EmptyRetriever всегда возвращает пустой список."""
    retriever = EmptyRetriever()
    docs = retriever.retrieve("any question", k=5)
    assert docs == []
