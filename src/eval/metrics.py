"""RAG evaluation metrics."""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate


def recall_at_k(
    retrieved_docs: list[Document], relevant_doc_ids: set[str], k: int
) -> float:
    """Recall@k = relevant_in_top_k / total_relevant."""
    if not relevant_doc_ids:
        return 0.0

    top_k = retrieved_docs[:k]
    retrieved_ids = {_get_doc_id(doc) for doc in top_k}

    relevant_retrieved = len(retrieved_ids & relevant_doc_ids)
    return relevant_retrieved / len(relevant_doc_ids)


def precision_at_k(
    retrieved_docs: list[Document], relevant_doc_ids: set[str], k: int
) -> float:
    """Precision@k = relevant_in_top_k / k."""
    if k == 0:
        return 0.0

    top_k = retrieved_docs[:k]
    retrieved_ids = {_get_doc_id(doc) for doc in top_k}

    relevant_retrieved = len(retrieved_ids & relevant_doc_ids)
    return relevant_retrieved / k


def mrr_at_k(
    retrieved_docs: list[Document], relevant_doc_ids: set[str], k: int
) -> float:
    """MRR@k = 1 / rank_of_first_relevant."""
    top_k = retrieved_docs[:k]

    for rank, doc in enumerate(top_k, start=1):
        doc_id = _get_doc_id(doc)
        if doc_id in relevant_doc_ids:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(
    retrieved_docs: list[Document], relevant_doc_ids: set[str], k: int
) -> float:
    """NDCG@k with binary relevance."""
    top_k = retrieved_docs[:k]

    dcg = 0.0
    for rank, doc in enumerate(top_k, start=1):
        doc_id = _get_doc_id(doc)
        relevance = 1.0 if doc_id in relevant_doc_ids else 0.0
        dcg += relevance / math.log2(rank + 1)

    num_relevant = len(relevant_doc_ids)
    idcg = 0.0
    for rank in range(1, min(k, num_relevant) + 1):
        idcg += 1.0 / math.log2(rank + 1)

    if idcg == 0.0:
        return 0.0

    return dcg / idcg


def _get_doc_id(doc: Document) -> str:
    """Extracts document ID from metadata."""
    meta = doc.metadata or {}
    return (
        meta.get("chunk_id") or meta.get("source") or meta.get("title") or str(id(doc))
    )


def compute_retrieval_metrics(
    retrieved_docs: list[Document],
    relevant_doc_ids: set[str],
    k_values: list[int] | None = None,
) -> dict[str, float]:
    """Computes retrieval metrics for given k values."""
    if k_values is None:
        k_values = [1, 3, 5, 10]
    metrics: dict[str, float] = {}

    for k in k_values:
        metrics[f"recall@{k}"] = recall_at_k(retrieved_docs, relevant_doc_ids, k)
        metrics[f"precision@{k}"] = precision_at_k(retrieved_docs, relevant_doc_ids, k)
        metrics[f"mrr@{k}"] = mrr_at_k(retrieved_docs, relevant_doc_ids, k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(retrieved_docs, relevant_doc_ids, k)

    return metrics


def compute_groundedness(answer: str, sources: list[Document]) -> float:
    """Checks if answer references sources. Returns 1.0 if sources section exists, 0.5 if mentions found, 0.0 otherwise."""
    answer_lower = answer.lower()
    has_sources_section = "📚 источники" in answer_lower or "источники:" in answer_lower

    has_source_mentions = False
    if sources:
        for source in sources[:3]:
            meta = source.metadata or {}
            title = meta.get("title", "")
            if title and title.lower() in answer_lower:
                has_source_mentions = True
                break

    if has_sources_section:
        return 1.0
    elif has_source_mentions:
        return 0.5
    else:
        return 0.0


async def llm_as_judge(
    question: str,
    answer: str,
    context: str,
    judge_model: Any,
) -> dict[str, float]:
    """Evaluates answer quality using LLM judge. Returns scores for correctness, completeness, clarity, usefulness."""
    logger = logging.getLogger(__name__)

    judge_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """Ты — эксперт-оценщик качества ответов AI-ассистента для подготовки к собеседованиям.

Оцени ответ по следующим критериям (каждый от 0.0 до 1.0):
1. Correctness (правильность): Насколько ответ технически корректен?
2. Completeness (полнота): Насколько полно ответ покрывает вопрос?
3. Clarity (ясность): Насколько ясно и понятно изложен ответ?
4. Usefulness (полезность): Насколько полезен ответ для подготовки к собеседованию?

ВАЖНО: Верни ТОЛЬКО валидный JSON объект без дополнительного текста, комментариев или markdown разметки.
Формат: {{"correctness": 0.0, "completeness": 0.0, "clarity": 0.0, "usefulness": 0.0}}
Замени 0.0 на реальные оценки от 0.0 до 1.0.""",
            ),
            (
                "human",
                """Вопрос: {question}

Контекст (источники):
{context}

Ответ:
{answer}

Оцени ответ по критериям и верни ТОЛЬКО JSON объект в формате:
{{"correctness": 0.0, "completeness": 0.0, "clarity": 0.0, "usefulness": 0.0}}""",
            ),
        ]
    )

    try:
        chain = judge_prompt | judge_model | StrOutputParser()
        response_text = await chain.ainvoke(
            {
                "question": question,
                "context": context or "(контекст не предоставлен)",
                "answer": answer,
            }
        )

        logger.debug(f"LLM-as-judge response (first 500 chars): {response_text[:500]}")

        code_block_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL
        )
        if code_block_match:
            try:
                scores = json.loads(code_block_match.group(1))
                return {
                    "correctness": float(scores.get("correctness", 0.0)),
                    "completeness": float(scores.get("completeness", 0.0)),
                    "clarity": float(scores.get("clarity", 0.0)),
                    "usefulness": float(scores.get("usefulness", 0.0)),
                }
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse JSON from code block: {e}")

        json_match = re.search(
            r'\{[^{}]*"correctness"[^{}]*(?:,"[^"]+"[^{}]*)*\}',
            response_text,
            re.DOTALL,
        )
        if json_match:
            try:
                scores = json.loads(json_match.group(0))
                return {
                    "correctness": float(scores.get("correctness", 0.0)),
                    "completeness": float(scores.get("completeness", 0.0)),
                    "clarity": float(scores.get("clarity", 0.0)),
                    "usefulness": float(scores.get("usefulness", 0.0)),
                }
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse JSON from first regex: {e}")

        json_match = re.search(
            r'\{[^{}]*"correctness"[^{}]*\}', response_text, re.DOTALL
        )
        if json_match:
            try:
                scores = json.loads(json_match.group(0))
                return {
                    "correctness": float(scores.get("correctness", 0.0)),
                    "completeness": float(scores.get("completeness", 0.0)),
                    "clarity": float(scores.get("clarity", 0.0)),
                    "usefulness": float(scores.get("usefulness", 0.0)),
                }
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse JSON from second regex: {e}")

        json_match = re.search(
            r'\{[^}]*"correctness"[^}]*"completeness"[^}]*"clarity"[^}]*"usefulness"[^}]*\}',
            response_text,
            re.DOTALL,
        )
        if json_match:
            try:
                scores = json.loads(json_match.group(0))
                return {
                    "correctness": float(scores.get("correctness", 0.0)),
                    "completeness": float(scores.get("completeness", 0.0)),
                    "clarity": float(scores.get("clarity", 0.0)),
                    "usefulness": float(scores.get("usefulness", 0.0)),
                }
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"Failed to parse JSON from third regex: {e}")

        logger.warning(
            f"Could not parse JSON from LLM response. Full response: {response_text[:1000]}"
        )

    except Exception as e:
        logger.warning(f"LLM-as-judge error: {e}", exc_info=True)

    return {
        "correctness": 0.0,
        "completeness": 0.0,
        "clarity": 0.0,
        "usefulness": 0.0,
    }
