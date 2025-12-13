from __future__ import annotations

from src.llm.memory import MemoryStore, Style


def test_memory_truncates_history() -> None:
    m = MemoryStore(max_messages=3)
    chat_id = 1
    m.append_user(chat_id, "u1")
    m.append_ai(chat_id, "a1")
    m.append_user(chat_id, "u2")
    m.append_ai(chat_id, "a2")
    msgs = m.get_history_messages(chat_id)
    assert len(msgs) == 3
    # Should keep last 3 messages: a1, u2, a2
    assert msgs[0].content == "a1"
    assert msgs[1].content == "u2"
    assert msgs[2].content == "a2"


def test_prefs_style_roundtrip() -> None:
    m = MemoryStore()
    user_id = 42
    assert m.get_prefs(user_id).style == Style.BRIEF
    m.set_style(user_id, Style.DETAILED)
    assert m.get_prefs(user_id).style == Style.DETAILED


