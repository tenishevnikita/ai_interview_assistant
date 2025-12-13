from __future__ import annotations

import html
import re

TG_LIMIT = 4096


_FENCE_RE = re.compile(r"```(\w+)?\n([\s\S]*?)```", re.MULTILINE)


def _render_text_html(text: str) -> str:
    # Minimal formatting: keep newlines.
    return html.escape(text).replace("\n", "\n")


def _render_code_html(code: str) -> str:
    # Telegram HTML supports <pre><code> for monospaced blocks.
    return f"<pre><code>{html.escape(code)}</code></pre>"


def _parse_fenced_blocks(text: str) -> list[tuple[str, str]]:
    """Return list of ('text'|'code', content) preserving order."""
    out: list[tuple[str, str]] = []
    last = 0
    for m in _FENCE_RE.finditer(text):
        if m.start() > last:
            out.append(("text", text[last : m.start()]))
        code = m.group(2) or ""
        out.append(("code", code.rstrip("\n")))
        last = m.end()
    if last < len(text):
        out.append(("text", text[last:]))
    return out


def _split_plain(text: str, limit: int) -> list[str]:
    text = text.strip("\n")
    if not text:
        return []
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    buf = ""
    for part in re.split(r"(\n\n+)", text):
        if not part:
            continue
        if len(buf) + len(part) <= limit:
            buf += part
            continue
        if buf:
            chunks.append(buf.strip("\n"))
            buf = ""
        if len(part) <= limit:
            buf = part
            continue
        # Too large paragraph: split by lines.
        line_buf = ""
        for line in part.splitlines(keepends=True):
            if len(line_buf) + len(line) <= limit:
                line_buf += line
            else:
                chunks.append(line_buf.strip("\n"))
                line_buf = line
        if line_buf.strip("\n"):
            buf = line_buf
    if buf.strip("\n"):
        chunks.append(buf.strip("\n"))
    return [c for c in chunks if c]


def format_and_split_for_telegram_html(text: str, limit: int = TG_LIMIT) -> list[str]:
    """Convert markdown-ish text with ``` fences into Telegram HTML and split safely."""
    blocks = _parse_fenced_blocks(text)
    rendered: list[str] = []
    for kind, content in blocks:
        if kind == "code":
            # Code block may still exceed the limit; split by lines and wrap each chunk.
            code_lines = content.splitlines(keepends=True)
            if not code_lines:
                rendered.append(_render_code_html(""))
                continue
            cur = ""
            for line in code_lines:
                if len(_render_code_html(cur + line)) <= limit:
                    cur += line
                else:
                    rendered.append(_render_code_html(cur.rstrip("\n")))
                    cur = line
            if cur or not rendered:
                rendered.append(_render_code_html(cur.rstrip("\n")))
        else:
            rendered.append(_render_text_html(content))

    # Join rendered blocks, then split without breaking <pre> blocks (they are standalone items).
    chunks: list[str] = []
    buf = ""
    for piece in rendered:
        if piece.startswith("<pre><code>"):
            if buf.strip():
                chunks.extend(_split_plain(buf, limit))
                buf = ""
            if len(piece) <= limit:
                chunks.append(piece)
            else:
                # Should not happen because we split code above, but guard anyway.
                chunks.extend(_split_plain(piece, limit))
            continue

        # Normal text html: accumulate and split if needed.
        if len(buf) + len(piece) <= limit:
            buf += piece
        else:
            chunks.extend(_split_plain(buf, limit))
            buf = piece

    if buf.strip():
        chunks.extend(_split_plain(buf, limit))

    # Telegram HTML dislikes completely empty messages.
    return [c for c in (c.strip() for c in chunks) if c]


