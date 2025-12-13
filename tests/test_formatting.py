from __future__ import annotations

from src.bot.formatting import TG_LIMIT, format_and_split_for_telegram_html


def test_formatting_splits_long_plain_text_under_limit() -> None:
    text = ("hello\n\n" * 2000).strip()
    chunks = format_and_split_for_telegram_html(text)
    assert chunks, "should produce at least one chunk"
    assert all(len(c) <= TG_LIMIT for c in chunks)


def test_formatting_renders_code_fence_as_pre_code() -> None:
    text = "Вот пример:\n```python\nprint('hi')\n```\nконец"
    chunks = format_and_split_for_telegram_html(text)
    joined = "\n".join(chunks)
    assert "<pre><code>" in joined
    assert "print(&#x27;hi&#x27;)" in joined or "print(&quot;hi&quot;)" in joined


def test_formatting_never_splits_inside_pre_block() -> None:
    code = "\n".join([f"line_{i}" for i in range(2000)])
    text = f"```text\n{code}\n```"
    chunks = format_and_split_for_telegram_html(text)
    assert chunks
    # Each chunk should be a standalone <pre><code>...</code></pre>
    assert all(c.startswith("<pre><code>") and c.endswith("</code></pre>") for c in chunks)
    assert all(len(c) <= TG_LIMIT for c in chunks)


