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

### Notes
- Telegram messages are sent in **HTML parse mode**; code fences like ```...``` will be rendered as `<pre><code>...</code></pre>`.
- If the vector store / retriever is not connected yet, the bot will answer with a disclaimer (“base is empty/index not connected”).
