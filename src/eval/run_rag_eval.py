"""RAG system evaluation script."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import traceback
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mistralai import ChatMistralAI

from src.eval.dataset import load_conversation_cases, load_retrieval_cases
from src.eval.metrics import (
    compute_groundedness,
    compute_retrieval_metrics,
    llm_as_judge,
)
from src.llm.memory import MemoryStore
from src.llm.rag_engine import RAGEngine
from src.vector_store.faiss_store import create_retriever

load_dotenv()


def _contains_all(haystack: str, needles: list[str]) -> bool:
    h = haystack.lower()
    return all(n.lower() in h for n in needles)


def _satisfies_groups(haystack: str, groups: list[list[str]]) -> bool:
    h = haystack.lower()
    for group in groups:
        if not group:
            continue
        if not any(alt.lower() in h for alt in group):
            return False
    return True


async def evaluate_retrieval(
    retriever, retrieval_cases: list, k_values: list[int] | None = None
) -> dict:
    if k_values is None:
        k_values = [1, 3, 5, 10]
    if not retrieval_cases:
        return {"error": "No retrieval cases provided"}

    all_metrics: dict[str, list[float]] = {}
    case_results = []

    for case in retrieval_cases:
        try:
            retrieved_docs = retriever.retrieve(case.question, k=max(k_values))
            relevant_ids = set(case.relevant_doc_ids)

            metrics = compute_retrieval_metrics(retrieved_docs, relevant_ids, k_values)

            for key, value in metrics.items():
                if key not in all_metrics:
                    all_metrics[key] = []
                all_metrics[key].append(value)

            case_results.append(
                {
                    "id": case.id,
                    "question": case.question,
                    "retrieved_count": len(retrieved_docs),
                    "metrics": metrics,
                }
            )
        except Exception as e:
            print(f"Error evaluating case {case.id}: {e}")
            continue

    avg_metrics = {
        key: sum(values) / len(values) if values else 0.0
        for key, values in all_metrics.items()
    }

    return {
        "n_cases": len(retrieval_cases),
        "avg_metrics": avg_metrics,
        "case_results": case_results,
    }


async def evaluate_end_to_end(
    engine: RAGEngine,
    conversation_cases: list,
    judge_model=None,
    compute_judge: bool = False,
) -> dict:
    rows: list[dict] = []
    rewrite_hits = 0
    groundedness_scores = []
    judge_scores: dict[str, list[float]] = {
        "correctness": [],
        "completeness": [],
        "clarity": [],
        "usefulness": [],
    }

    for case in conversation_cases:
        chat_id = hash(case.id) % 1000000
        user_id = chat_id

        engine._memory.clear_history(chat_id)
        for msg in case.history:
            if msg.role == "user":
                engine._memory.append_user(chat_id, msg.text)
            elif msg.role == "assistant":
                engine._memory.append_ai(chat_id, msg.text)

        try:
            answer, standalone, docs, context = await engine.answer_with_details(
                chat_id=chat_id, user_id=user_id, user_text=case.user_message
            )
        except Exception as e:
            print(f"Error processing case {case.id}: {e}")
            continue

        if case.expected_standalone_question_groups:
            rewrite_ok = _satisfies_groups(
                standalone, case.expected_standalone_question_groups
            )
        else:
            rewrite_ok = _contains_all(
                standalone, case.expected_standalone_question_contains
            )
        rewrite_hits += int(rewrite_ok)

        sources = docs
        if not context:
            context = "(контекст пуст)"

        groundedness = compute_groundedness(answer, sources)
        groundedness_scores.append(groundedness)

        judge_result = {}
        if compute_judge and judge_model:
            try:
                judge_result = await llm_as_judge(
                    case.user_message, answer, context, judge_model
                )
                if judge_result and any(v > 0.0 for v in judge_result.values()):
                    for key, value in judge_result.items():
                        judge_scores[key].append(value)
                else:
                    print(
                        f"Warning: LLM-as-judge returned all zeros for case {case.id}"
                    )
                    for key, value in judge_result.items():
                        judge_scores[key].append(value)
            except Exception as e:
                print(f"Error in LLM-as-judge for case {case.id}: {e}")
                traceback.print_exc()
                judge_result = {
                    "correctness": 0.0,
                    "completeness": 0.0,
                    "clarity": 0.0,
                    "usefulness": 0.0,
                }

        rows.append(
            {
                "id": case.id,
                "tags": case.tags,
                "user_message": case.user_message,
                "standalone_question": standalone,
                "rewrite_ok": rewrite_ok,
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "answer_len": len(answer),
                "groundedness": groundedness,
                "judge_scores": judge_result,
            }
        )

    avg_groundedness = (
        sum(groundedness_scores) / len(groundedness_scores)
        if groundedness_scores
        else 0.0
    )
    avg_judge_scores = {
        key: sum(values) / len(values) if values else 0.0
        for key, values in judge_scores.items()
    }

    return {
        "n_cases": len(conversation_cases),
        "rewrite_contains_rate": (
            (rewrite_hits / len(conversation_cases)) if conversation_cases else 0.0
        ),
        "avg_groundedness": avg_groundedness,
        "avg_judge_scores": avg_judge_scores,
        "rows": rows,
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description="RAG system evaluation")
    parser.add_argument(
        "--conversation-dataset", default="data/validation_conversation.jsonl"
    )
    parser.add_argument(
        "--retrieval-dataset",
        default="",
        help="Path to retrieval evaluation dataset (JSONL)",
    )
    parser.add_argument(
        "--index-path", default="data/faiss_index", help="Path to FAISS index"
    )
    parser.add_argument("--model", default="mistral-small-latest")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--judge-model", default="", help="Model for LLM-as-judge (empty to skip)"
    )
    parser.add_argument(
        "--out", default="", help="Optional: write JSON report to a file"
    )
    args = parser.parse_args()

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise SystemExit("MISTRAL_API_KEY is not set")

    judge_model = None
    if args.judge_model:
        judge_model = ChatMistralAI(
            api_key=api_key, model=args.judge_model, temperature=0.0
        )

    conversation_cases = load_conversation_cases(args.conversation_dataset)
    retrieval_cases = []
    if args.retrieval_dataset and Path(args.retrieval_dataset).exists():
        retrieval_cases = load_retrieval_cases(args.retrieval_dataset)

    memory = MemoryStore()
    retriever = None
    try:
        index_path = Path(args.index_path)
        if index_path.exists():
            retriever = create_retriever(index_path)
            print(f"✓ Загружен ретривер из {index_path}")
        else:
            print(f"⚠ Индекс не найден: {index_path}, работаем без ретривера")
    except Exception as e:
        print(f"⚠ Ошибка загрузки ретривера: {e}, работаем без ретривера")

    engine = RAGEngine(memory=memory, retriever=retriever)

    retrieval_report = {}
    if retrieval_cases and retriever:
        print("\n📊 Оценка ретривера...")
        retrieval_report = await evaluate_retrieval(retriever, retrieval_cases)

    print("\n📊 Оценка end-to-end системы...")
    e2e_report = await evaluate_end_to_end(
        engine,
        conversation_cases,
        judge_model=judge_model,
        compute_judge=bool(judge_model),
    )

    report = {
        "retrieval": retrieval_report,
        "end_to_end": e2e_report,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n✓ Отчет сохранен в {args.out}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
