"""Тесты для метрик оценки RAG системы."""

from __future__ import annotations

import pytest
from langchain_core.documents import Document

from src.eval.metrics import (
    compute_groundedness,
    compute_retrieval_metrics,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def test_recall_at_k() -> None:
    """Тест метрики Recall@k."""
    # Создаем тестовые документы
    docs = [
        Document(page_content="doc1", metadata={"chunk_id": "doc1"}),
        Document(page_content="doc2", metadata={"chunk_id": "doc2"}),
        Document(page_content="doc3", metadata={"chunk_id": "doc3"}),
        Document(page_content="doc4", metadata={"chunk_id": "doc4"}),
    ]

    # Все релевантные документы найдены
    relevant = {"doc1", "doc2"}
    assert recall_at_k(docs, relevant, k=2) == 1.0
    assert recall_at_k(docs, relevant, k=3) == 1.0

    # Только один найден
    assert recall_at_k(docs, relevant, k=1) == 0.5

    # Нет релевантных документов
    assert recall_at_k(docs, set(), k=2) == 0.0

    # Нет релевантных в топ-k
    assert recall_at_k(docs, {"doc5"}, k=2) == 0.0


def test_precision_at_k() -> None:
    """Тест метрики Precision@k."""
    docs = [
        Document(page_content="doc1", metadata={"chunk_id": "doc1"}),
        Document(page_content="doc2", metadata={"chunk_id": "doc2"}),
        Document(page_content="doc3", metadata={"chunk_id": "doc3"}),
    ]

    relevant = {"doc1", "doc2"}

    # Оба релевантных в топ-2
    assert precision_at_k(docs, relevant, k=2) == 1.0

    # Один релевантный в топ-2
    assert precision_at_k(docs, relevant, k=3) == pytest.approx(2.0 / 3.0)

    # Нет релевантных
    assert precision_at_k(docs, {"doc5"}, k=2) == 0.0


def test_mrr_at_k() -> None:
    """Тест метрики MRR@k."""
    docs = [
        Document(page_content="doc1", metadata={"chunk_id": "doc1"}),
        Document(page_content="doc2", metadata={"chunk_id": "doc2"}),
        Document(page_content="doc3", metadata={"chunk_id": "doc3"}),
    ]

    relevant = {"doc2"}

    # Первый релевантный на позиции 2
    assert mrr_at_k(docs, relevant, k=3) == pytest.approx(1.0 / 2.0)

    # Первый релевантный на позиции 1
    assert mrr_at_k(docs, {"doc1"}, k=3) == 1.0

    # Нет релевантных
    assert mrr_at_k(docs, {"doc5"}, k=3) == 0.0


def test_ndcg_at_k() -> None:
    """Тест метрики NDCG@k."""
    docs = [
        Document(page_content="doc1", metadata={"chunk_id": "doc1"}),
        Document(page_content="doc2", metadata={"chunk_id": "doc2"}),
        Document(page_content="doc3", metadata={"chunk_id": "doc3"}),
    ]

    relevant = {"doc1", "doc2"}

    # Идеальный случай: оба релевантных в начале
    ndcg = ndcg_at_k(docs, relevant, k=2)
    assert ndcg == pytest.approx(1.0, abs=0.01)

    # Один релевантный в начале
    ndcg = ndcg_at_k(docs, {"doc1"}, k=2)
    assert 0.0 < ndcg <= 1.0

    # Нет релевантных
    assert ndcg_at_k(docs, {"doc5"}, k=2) == 0.0


def test_compute_retrieval_metrics() -> None:
    """Тест вычисления всех метрик ретривера."""
    docs = [
        Document(page_content="doc1", metadata={"chunk_id": "doc1"}),
        Document(page_content="doc2", metadata={"chunk_id": "doc2"}),
        Document(page_content="doc3", metadata={"chunk_id": "doc3"}),
    ]

    relevant = {"doc1", "doc2"}
    metrics = compute_retrieval_metrics(docs, relevant, k_values=[1, 2, 3])

    assert "recall@1" in metrics
    assert "precision@1" in metrics
    assert "mrr@1" in metrics
    assert "ndcg@1" in metrics

    assert "recall@3" in metrics
    assert "precision@3" in metrics

    # Проверяем, что все значения в диапазоне [0, 1]
    for value in metrics.values():
        assert 0.0 <= value <= 1.0


def test_groundedness() -> None:
    """Тест метрики groundedness."""
    sources = [
        Document(page_content="test", metadata={"title": "Test Document"}),
    ]

    # Ответ со ссылками на источники
    answer_with_sources = "Ответ на вопрос.\n\n📚 Источники:\n• Test Document"
    assert compute_groundedness(answer_with_sources, sources) == 1.0

    # Ответ с упоминанием источника в тексте
    answer_with_mention = "Согласно Test Document, ответ такой..."
    assert compute_groundedness(answer_with_mention, sources) == 0.5

    # Ответ без источников
    answer_no_sources = "Просто ответ без ссылок."
    assert compute_groundedness(answer_no_sources, sources) == 0.0

    # Пустой список источников
    assert compute_groundedness("Ответ", []) == 0.0
