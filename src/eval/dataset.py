from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Message:
    role: str  # "user" | "assistant"
    text: str


@dataclass(frozen=True)
class ConversationCase:
    id: str
    history: list[Message]
    user_message: str
    expected_standalone_question_contains: list[str]
    # New format: AND of OR-groups. For each group, at least one alternative must appear.
    # Example: [["пример", "алгоритм"], ["градиент", "boost"]]
    expected_standalone_question_groups: list[list[str]]
    style: str  # "brief" | "detailed" | "socratic"
    tags: list[str]


def load_conversation_cases(path: str | Path) -> list[ConversationCase]:
    p = Path(path)
    cases: list[ConversationCase] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        history = [Message(**m) for m in obj.get("history", [])]
        cases.append(
            ConversationCase(
                id=obj["id"],
                history=history,
                user_message=obj["user_message"],
                expected_standalone_question_contains=obj.get("expected_standalone_question_contains", []),
                expected_standalone_question_groups=obj.get("expected_standalone_question_groups", []),
                style=obj.get("style", "brief"),
                tags=obj.get("tags", []),
            )
        )
    return cases
