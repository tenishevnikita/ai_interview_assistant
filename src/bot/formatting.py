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
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)([^_\n]+?)(?<!_)_(?!_)")


def _escape_html_text(text: str) -> str:
    """
    Экранирует HTML символы в тексте, но сохраняет уже существующие HTML теги.
    Использует простой подход: экранирует всё, затем восстанавливает валидные теги.
    """
    # Экранируем всё
    escaped = html.escape(text)

    # Восстанавливаем валидные HTML теги для Telegram
    # Примечание: Telegram HTML не поддерживает <br> тег
    valid_tags = ["<b>", "</b>", "<i>", "</i>", "<code>", "</code>", "<pre>", "</pre>"]
    for tag in valid_tags:
        escaped_tag = html.escape(tag)
        escaped = escaped.replace(escaped_tag, tag)

    return escaped


def _markdown_to_html(text: str) -> str:
    """
    Конвертирует базовые Markdown элементы в HTML для Telegram.

    Порядок важен:
    1. Inline код (чтобы не трогать код внутри)
    2. Жирный текст
    3. Курсив
    """
    # Обрабатываем inline код - заменяем на плейсхолдеры
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

    # Затем обрабатываем жирный текст
    def replace_bold(match: re.Match) -> str:
        content = match.group(1) or match.group(2)
        return f"<b>{html.escape(content)}</b>"

    text = _BOLD_RE.sub(replace_bold, text)

    # Затем обрабатываем курсив
    def replace_italic(match: re.Match) -> str:
        content = match.group(1) or match.group(2)
        return f"<i>{html.escape(content)}</i>"

    text = _ITALIC_RE.sub(replace_italic, text)

    # Восстанавливаем inline код
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

    # Обрабатываем заголовки: применяем форматирование внутри них, затем оборачиваем в <b>
    for placeholder, heading_text in heading_placeholders.items():
        # Применяем форматирование к тексту заголовка
        processed_heading = heading_text

        # Обрабатываем inline код
        processed_heading = _INLINE_CODE_RE.sub(
            lambda m: f"<code>{html.escape(m.group(1))}</code>",
            processed_heading
        )

        # Убираем маркеры жирного текста (весь заголовок будет жирным)
        processed_heading = _BOLD_RE.sub(
            lambda m: html.escape(m.group(1) or m.group(2)),
            processed_heading
        )

        # Обрабатываем курсив
        processed_heading = _ITALIC_RE.sub(
            lambda m: f"<i>{html.escape(m.group(1) or m.group(2))}</i>",
            processed_heading
        )

        # Экранируем остальной HTML
        processed_heading = html.escape(processed_heading)

        # Восстанавливаем теги кода и курсива (которые были экранированы)
        # Находим код в исходном тексте
        code_match = _INLINE_CODE_RE.search(heading_text)
        if code_match:
            code_content = code_match.group(1)
            escaped_code = html.escape(code_content)
            escaped_code_tag_open = html.escape("<code>")
            escaped_code_tag_close = html.escape("</code>")
            # Заменяем экранированные теги и содержимое на правильные теги
            processed_heading = processed_heading.replace(
                escaped_code_tag_open + escaped_code + escaped_code_tag_close,
                f"<code>{escaped_code}</code>"
            )

        # Находим курсив в исходном тексте
        italic_match = _ITALIC_RE.search(heading_text)
        if italic_match:
            italic_content = italic_match.group(1) or italic_match.group(2)
            escaped_italic = html.escape(italic_content)
            escaped_italic_tag_open = html.escape("<i>")
            escaped_italic_tag_close = html.escape("</i>")
            # Заменяем экранированные теги и содержимое на правильные теги
            processed_heading = processed_heading.replace(
                escaped_italic_tag_open + escaped_italic + escaped_italic_tag_close,
                f"<i>{escaped_italic}</i>"
            )

        # Оборачиваем весь заголовок в <b>
        heading_html = f"<b>{processed_heading}</b>"
        text = text.replace(placeholder, heading_html)

    # Экранируем HTML символы, но сохраняем валидные теги
    text = _escape_html_text(text)

    # Telegram HTML не поддерживает <br> тег - переносы строк остаются как \n
    # Telegram сам обработает переносы строк при отображении
    return text


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
