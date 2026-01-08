## AI Interview Assistant (Telegram bot, RAG baseline)

### Prerequisites
- Python **3.12+**
- [`uv`](https://github.com/astral-sh/uv) (recommended)

### Setup
1) Create `.env` from template:

```bash
cp env.example .env
```

2) Fill variables in `.env`:
- `TELEGRAM_BOT_TOKEN` — get it from BotFather
- `MISTRAL_API_KEY` — Mistral API key

3) Install deps:

```bash
uv sync
```

### Run the bot (polling)

```bash
uv run python -m src.bot.main
```

### Linting & Formatting

Check code with ruff:

```bash
make lint
```

Format code:

```bash
make format
```

Run all checks (lint + format + tests):

```bash
make check
```

Or install pre-commit hooks:

```bash
uv run pre-commit install
```

### Tests

- Unit tests (no network):

```bash
uv run pytest -m "not e2e"
# or
make test
```

- E2E tests (requires `MISTRAL_API_KEY` and network):

```bash
uv run pytest -m e2e
# or
make test-e2e
```

### Eval (rewrite-focused, for your report)

```bash
uv run python -m src.eval.run_eval --dataset data/validation_conversation.jsonl
```

See `docs/eval_metrics.md` for the suggested metrics and evaluation protocol.

### Notes
- Telegram messages are sent in **HTML parse mode**; code fences like ```...``` will be rendered as `<pre><code>...</code></pre>`.
- If the vector store / retriever is not connected yet, the bot will answer with a disclaimer (“base is empty/index not connected”).
