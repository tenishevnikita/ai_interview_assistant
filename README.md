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
- `ADMIN_USER_IDS` — (optional) comma-separated list of Telegram user IDs for admin access
- `TEMP_FILES_DIR` — (optional) directory for temporary files (default: `data/temp`)

3) Install deps:

```bash
uv sync
```

### Building the Knowledge Base Index

Before running the bot, you need to build the FAISS index:

```bash
# 1. Download source data (HTML files)
uv run python -m src.data_processing.download_handbook

# 2. Extract text and create chunks
uv run python -m src.data_processing.extract_handbook

# 3. Build FAISS index
uv run python -m src.data_processing.build_index --test
```

The index will be saved to `data/faiss_index/`. The bot will automatically load it on startup.

See `docs/data_pipeline.md` for detailed information about the data pipeline.

### Run the bot (polling)

```bash
uv run python -m src.bot.main
```

The bot will automatically load the FAISS index if it exists in `data/faiss_index/`. If the index is not found, the bot will work without the knowledge base (with a disclaimer in responses).

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

### Admin Features

Admins can upload PDF files to the bot:

1. Add your Telegram user ID to `ADMIN_USER_IDS` in `.env` (comma-separated)
2. Send `/admin` command to see admin panel
3. Upload PDF files — they will be saved to the temp directory

**Note:** The main parsing and indexing logic for uploaded files will be implemented later.

### Notes
- Telegram messages are sent in **HTML parse mode**; code fences like ```...``` will be rendered as `<pre><code>...</code></pre>`.
- If the FAISS index is not found or empty, the bot will work without the knowledge base and show a disclaimer in responses.
- The bot automatically formats answers and splits long messages (>4096 characters) into multiple parts.
- Sources are automatically added to answers when documents are retrieved from the knowledge base.
