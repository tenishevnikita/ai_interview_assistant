## Метрики и протокол оценки (для отчёта)

### Что можно валидировать уже сейчас (без RAG коллеги)
Фокус на твоей зоне (Conversation & Prompt + Telegram UX):

- **Rewrite success rate**: доля кейсов, где standalone-вопрос содержит ожидаемые ключевые фразы.
  - Датасет: `data/validation_conversation.jsonl`
  - Прогон: `uv run python -m src.eval.run_eval --dataset data/validation_conversation.jsonl`
  - Метрика: `rewrite_contains_rate`
  - Примечание: для устойчивости к перефразированию используется проверка **AND of OR-groups** (например: ["пример" ИЛИ "алгоритм"] И ["градиент" ИЛИ "boost"]).

- **Telegram constraints (unit)**:
  - каждое сообщение ≤ 4096 символов
  - кодовые блоки не рвутся внутри `<pre><code>...</code></pre>`
  - тесты: `uv run pytest -m "not e2e"`

### Что добавляется после подключения RAG (коллега закончит)
Когда `Retriever.retrieve()` начнёт возвращать документы, можно считать метрики итоговой системы:

- **Answer groundedness (контекстность)**:
  - доля ответов, которые используют информацию из retrieved chunks (например, наличие цитат/ссылок на источники)
  - прокси-метрика: наличие секции “Источники” и совпадение `chunk_id/source`

- **Retrieval quality** (делает коллега, но в отчёте важно упомянуть):
  - Recall@k / MRR@k по labeled QA (если появится)
  - Re-ranker gain: сравнение до/после reranking

- **End-to-end answer quality**:
  - human eval (5-балльная шкала) по: correctness, completeness, clarity, usefulness
  - или LLM-as-judge (второй LLM оценивает по рубрике) — важно фиксировать промпт судьи и seed/temperature.

### E2E тесты с Mistral (для CI/демо)
Есть e2e тест для rewrite-цепочки (требует сеть и `MISTRAL_API_KEY`):

```bash
uv run pytest -m e2e
```

Рекомендация: держать e2e тесты короткими и устойчивыми (проверять только ключевые инварианты, а не точный текст).


