from __future__ import annotations

import argparse
import json
import os

from langchain_mistralai import ChatMistralAI
from langchain_core.messages import AIMessage, HumanMessage

from src.eval.dataset import load_conversation_cases
from src.llm.chains import build_answer_chain, build_rewrite_chain
from src.llm.memory import Style


def _contains_all(haystack: str, needles: list[str]) -> bool:
    """Legacy check: all substrings must appear."""
    h = haystack.lower()
    return all(n.lower() in h for n in needles)


def _satisfies_groups(haystack: str, groups: list[list[str]]) -> bool:
    """AND of OR-groups: each group must have >=1 alternative present."""
    h = haystack.lower()
    for group in groups:
        if not group:
            continue
        if not any(alt.lower() in h for alt in group):
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Conversation eval (rewrite + answer).")
    parser.add_argument("--dataset", default="data/validation_conversation.jsonl")
    parser.add_argument("--model", default="mistral-small-latest")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--out", default="", help="Optional: write JSON report to a file")
    args = parser.parse_args()

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise SystemExit("MISTRAL_API_KEY is not set")

    model = ChatMistralAI(api_key=api_key, model=args.model, temperature=args.temperature)
    rewrite = build_rewrite_chain(model)
    answer = build_answer_chain(model)

    cases = load_conversation_cases(args.dataset)
    rows: list[dict] = []
    rewrite_hits = 0

    for case in cases:
        history_msgs = []
        for m in case.history:
            if m.role == "user":
                history_msgs.append(HumanMessage(content=m.text))
            else:
                history_msgs.append(AIMessage(content=m.text))

        standalone = rewrite.invoke({"history": history_msgs, "input": case.user_message})  # sync for speed
        standalone = (standalone or "").strip()

        # Scoring:
        # - Prefer semantic-ish groups if provided (robust to wording like "пример" vs "алгоритм",
        #   Russian vs English terms, "3-й" vs "третий").
        # - Fallback to legacy strict substring list for backwards compatibility.
        if case.expected_standalone_question_groups:
            ok = _satisfies_groups(standalone, case.expected_standalone_question_groups)
        else:
            ok = _contains_all(standalone, case.expected_standalone_question_contains)
        rewrite_hits += int(ok)

        # Answer with empty context for now (colleague's RAG not connected yet)
        style = case.style
        if style not in {s.value for s in Style}:
            style = Style.BRIEF.value

        resp = answer.invoke({"question": standalone or case.user_message, "context": "(контекст пуст)", "style": style})
        resp = (resp or "").strip()

        rows.append(
            {
                "id": case.id,
                "tags": case.tags,
                "user_message": case.user_message,
                "standalone_question": standalone,
                "expected_contains": case.expected_standalone_question_contains,
                "expected_groups": case.expected_standalone_question_groups,
                "rewrite_ok": ok,
                "style": style,
                "answer_len": len(resp),
            }
        )

    report = {
        "dataset": args.dataset,
        "n": len(cases),
        "rewrite_contains_rate": (rewrite_hits / len(cases)) if cases else 0.0,
        "rows": rows,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


