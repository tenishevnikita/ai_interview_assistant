from __future__ import annotations

import os

import pytest
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import AIMessage, HumanMessage

from src.llm.chains import build_rewrite_chain


pytestmark = pytest.mark.e2e


@pytest.mark.asyncio
async def test_rewrite_followup_gradient_boosting() -> None:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        pytest.skip("MISTRAL_API_KEY is not set")

    model = ChatMistralAI(api_key=api_key, model="mistral-small-latest", temperature=0.0)
    chain = build_rewrite_chain(model)

    history = [
        HumanMessage(content="Что такое градиентный бустинг?"),
        AIMessage(content="Градиентный бустинг — это ансамблевый метод..."),
    ]
    followup = "уточни примеры алгоритмов"
    standalone = await chain.ainvoke({"history": history, "input": followup})
    s = (standalone or "").lower()
    # E2E tests with LLM must be robust: check semantic invariants, not exact phrasing.
    # We expect the follow-up to be rewritten into a standalone question about algorithms of gradient boosting.
    assert "алгоритм" in s
    assert ("градиент" in s and "буст" in s) or "boost" in s


