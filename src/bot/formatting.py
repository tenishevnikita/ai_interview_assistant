from __future__ import annotations

import html
import re

TG_LIMIT = 4096


_FENCE_RE = re.compile(r"```(\w+)?\n([\s\S]*?)```", re.MULTILINE)
# Headings: # Heading, ## Heading, ### Heading, #### Heading
_HEADING_RE = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)
# Inline code: `code` (но не внутри блоков кода)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
# Bold: **text** or __text__ (но не внутри inline кода)
_BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*|(?<![_*])__([^_\n]+?)__(?![_*])")
# Italic: *text* or _text_ (но не **text** или __text__)
# Используем lookahead/lookbehind чтобы не конфликтовать с жирным
_ITALIC_RE = re.compile(
    r"(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)"
)


def _escape_html_text(text: str) -> str:
    """Escapes HTML but preserves valid Telegram HTML tags."""
    placeholders: dict[str, str] = {}
    placeholder_counter = 0

    a_tag_pattern = re.compile(r"<a\s+[^>]+>")

    def protect_a_tag(match):
        nonlocal placeholder_counter
        tag = match.group(0)
        placeholder = f"__PLACEHOLDER_A_TAG_{placeholder_counter}__"
        placeholders[placeholder] = tag
        placeholder_counter += 1
        return placeholder

    text = a_tag_pattern.sub(protect_a_tag, text)

    def protect_a_close(match):
        nonlocal placeholder_counter
        tag = match.group(0)
        placeholder = f"__PLACEHOLDER_A_CLOSE_{placeholder_counter}__"
        placeholders[placeholder] = tag
        placeholder_counter += 1
        return placeholder

    text = re.sub(r"</a>", protect_a_close, text)

    valid_tags = ["<b>", "</b>", "<i>", "</i>", "<code>", "</code>", "<pre>", "</pre>"]
    for tag in valid_tags:
        placeholder = f"__PLACEHOLDER_{placeholder_counter}__"
        placeholders[placeholder] = tag
        text = text.replace(tag, placeholder)
        placeholder_counter += 1

    escaped = html.escape(text)

    for placeholder, tag in placeholders.items():
        escaped = escaped.replace(placeholder, tag)

    return escaped


def _markdown_to_html(text: str) -> str:
    """Converts basic Markdown to Telegram HTML."""
    code_placeholders: dict[str, str] = {}
    code_counter = 0

    def replace_inline_code(match: re.Match) -> str:
        nonlocal code_counter
        code = match.group(1)
        placeholder = f"PLACEHOLDERINLINECODE{code_counter}PLACEHOLDER"
        code_placeholders[placeholder] = f"<code>{html.escape(code)}</code>"
        code_counter += 1
        return placeholder

    text = _INLINE_CODE_RE.sub(replace_inline_code, text)

    def replace_bold(match: re.Match) -> str:
        content = match.group(1) or match.group(2)
        return f"<b>{html.escape(content)}</b>"

    text = _BOLD_RE.sub(replace_bold, text)

    def replace_italic(match: re.Match) -> str:
        content = match.group(1) or match.group(2)
        return f"<i>{html.escape(content)}</i>"

    text = _ITALIC_RE.sub(replace_italic, text)

    for placeholder, html_code in code_placeholders.items():
        text = text.replace(placeholder, html_code)

    return text


def _render_text_html(text: str) -> str:
    """
    Конвертирует Markdown в HTML для Telegram и экранирует остальное.
    Сохраняет переносы строк как есть (Telegram HTML не поддерживает <br> тег).
    """
    # Сначала обрабатываем заголовки - заменяем на плейсхолдеры
    heading_placeholders: dict[str, str] = {}
    heading_counter = 0

    def replace_heading_placeholder(match: re.Match) -> str:
        nonlocal heading_counter
        heading_text = match.group(1).strip()
        placeholder = f"PLACEHOLDERHEADING{heading_counter}PLACEHOLDER"
        heading_placeholders[placeholder] = heading_text
        heading_counter += 1
        return placeholder

    text = _HEADING_RE.sub(replace_heading_placeholder, text)

    # Конвертируем остальной Markdown в HTML
    text = _markdown_to_html(text)

    for placeholder, heading_text in heading_placeholders.items():
        processed_heading = heading_text

        processed_heading = _INLINE_CODE_RE.sub(
            lambda m: f"<code>{html.escape(m.group(1))}</code>", processed_heading
        )

        processed_heading = _BOLD_RE.sub(
            lambda m: html.escape(m.group(1) or m.group(2)), processed_heading
        )

        processed_heading = _ITALIC_RE.sub(
            lambda m: f"<i>{html.escape(m.group(1) or m.group(2))}</i>",
            processed_heading,
        )

        processed_heading = html.escape(processed_heading)

        code_match = _INLINE_CODE_RE.search(heading_text)
        if code_match:
            code_content = code_match.group(1)
            escaped_code_tag_open = html.escape("<code>")
            escaped_code_tag_close = html.escape("</code>")
            processed_heading = processed_heading.replace(
                escaped_code_tag_open
                + html.escape(code_content)
                + escaped_code_tag_close,
                f"<code>{code_content}</code>",
            )

        italic_match = _ITALIC_RE.search(heading_text)
        if italic_match:
            italic_content = italic_match.group(1) or italic_match.group(2)
            escaped_italic_tag_open = html.escape("<i>")
            escaped_italic_tag_close = html.escape("</i>")
            processed_heading = processed_heading.replace(
                escaped_italic_tag_open
                + html.escape(italic_content)
                + escaped_italic_tag_close,
                f"<i>{italic_content}</i>",
            )

        heading_html = f"<b>{processed_heading}</b>"
        text = text.replace(placeholder, heading_html)

    text = _escape_html_text(text)
    return text


def _render_code_html(code: str) -> str:
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
    """Converts Markdown to Telegram HTML and splits into messages."""
    blocks = _parse_fenced_blocks(text)
    rendered: list[str] = []
    for kind, content in blocks:
        if kind == "code":
            rendered.append(_render_code_html(content))
        else:
            rendered.append(_render_text_html(content))

    chunks: list[str] = []
    buf = ""

    for piece in rendered:
        piece_len = len(piece)

        if not buf.strip() and piece_len <= limit:
            buf = piece
            continue

        combined_len = len(buf) + len(piece) if buf else piece_len

        if combined_len <= limit:
            if buf:
                buf = f"{buf}\n{piece}"
            else:
                buf = piece
        else:
            if buf.strip():
                if buf.startswith("<pre><code>"):
                    chunks.append(buf)
                else:
                    chunks.extend(_split_plain(buf, limit))
                buf = ""

            if piece.startswith("<pre><code>"):
                if piece_len <= limit:
                    buf = piece
                else:
                    code_match = re.search(
                        r"<pre><code>(.*?)</code></pre>", piece, re.DOTALL
                    )
                    if code_match:
                        code_content = code_match.group(1)
                        code_lines = code_content.splitlines(keepends=True)
                        code_buf = ""
                        for line in code_lines:
                            line_html = _render_code_html(code_buf + line)
                            if len(line_html) <= limit:
                                code_buf += line
                            else:
                                if code_buf:
                                    chunks.append(
                                        _render_code_html(code_buf.rstrip("\n"))
                                    )
                                code_buf = line
                        if code_buf.strip():
                            buf = _render_code_html(code_buf.rstrip("\n"))
                    else:
                        chunks.append(piece)
            else:
                chunks.extend(_split_plain(piece, limit))

    if buf.strip():
        if buf.startswith("<pre><code>"):
            chunks.append(buf)
        else:
            chunks.extend(_split_plain(buf, limit))

    return [c for c in (c.strip() for c in chunks) if c]
