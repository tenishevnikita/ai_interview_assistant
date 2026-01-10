from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class Style(StrEnum):
    BRIEF = "brief"
    DETAILED = "detailed"


@dataclass(frozen=True)
class UserPrefs:
    style: Style = Style.BRIEF


class MemoryStore:
    """In-memory storage for chat histories and user preferences (baseline).

    Notes:
    - Keyed by Telegram `chat_id` for history (group chats supported).
    - Keyed by Telegram `user_id` for preferences (style).
    """

    def __init__(self, max_messages: int = 12) -> None:
        self._max_messages = max_messages
        self._histories: dict[int, list[BaseMessage]] = defaultdict(list)
        self._prefs: dict[int, UserPrefs] = {}

    def get_history_messages(self, chat_id: int) -> list[BaseMessage]:
        return list(self._histories[chat_id])

    def append_user(self, chat_id: int, text: str) -> None:
        self._append(chat_id, HumanMessage(content=text))

    def append_ai(self, chat_id: int, text: str) -> None:
        self._append(chat_id, AIMessage(content=text))

    def _append(self, chat_id: int, msg: BaseMessage) -> None:
        hist = self._histories[chat_id]
        hist.append(msg)
        if len(hist) > self._max_messages:
            self._histories[chat_id] = hist[-self._max_messages :]

    def get_prefs(self, user_id: int) -> UserPrefs:
        return self._prefs.get(user_id, UserPrefs())

    def set_style(self, user_id: int, style: Style) -> None:
        self._prefs[user_id] = UserPrefs(style=style)

    def clear_history(self, chat_id: int) -> None:
        """Очищает историю диалога для указанного чата."""
        self._histories[chat_id] = []
