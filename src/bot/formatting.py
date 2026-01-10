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
    Использует простой подход: сначала защищаем валидные HTML теги, затем экранируем остальное.
    """
    # Сначала защищаем валидные HTML теги, заменяя их на плейсхолдеры
    # Это нужно чтобы они не были экранированы
    placeholders: dict[str, str] = {}
    placeholder_counter = 0
    
    # Защищаем теги <a> с атрибутами (самые сложные)
    a_tag_pattern = re.compile(r'<a\s+[^>]+>')
    def protect_a_tag(match):
        nonlocal placeholder_counter
        tag = match.group(0)
        placeholder = f"__PLACEHOLDER_A_TAG_{placeholder_counter}__"
        placeholders[placeholder] = tag
        placeholder_counter += 1
        return placeholder
    text = a_tag_pattern.sub(protect_a_tag, text)
    
    # Защищаем закрывающие теги </a>
    def protect_a_close(match):
        nonlocal placeholder_counter
        tag = match.group(0)
        placeholder = f"__PLACEHOLDER_A_CLOSE_{placeholder_counter}__"
        placeholders[placeholder] = tag
        placeholder_counter += 1
        return placeholder
    text = re.sub(r'</a>', protect_a_close, text)
    
    # Защищаем другие валидные теги
    valid_tags = ["<b>", "</b>", "<i>", "</i>", "<code>", "</code>", "<pre>", "</pre>"]
    for tag in valid_tags:
        placeholder = f"__PLACEHOLDER_{placeholder_counter}__"
        placeholders[placeholder] = tag
        text = text.replace(tag, placeholder)
        placeholder_counter += 1
    
    # Экранируем всё остальное
    escaped = html.escape(text)
    
    # Восстанавливаем защищенные теги
    for placeholder, tag in placeholders.items():
        escaped = escaped.replace(placeholder, tag)

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
    """
    Конвертирует Markdown в HTML для Telegram и разбивает на сообщения.

    Блоки кода объединяются с текстом в одном сообщении, если это возможно.
    Разбиение происходит только если сообщение превышает лимит.
    """
    blocks = _parse_fenced_blocks(text)
    rendered: list[str] = []
    for kind, content in blocks:
        if kind == "code":
            # Рендерим код как HTML блок
            rendered.append(_render_code_html(content))
        else:
            rendered.append(_render_text_html(content))

    # Объединяем блоки в сообщения, стараясь включать код вместе с текстом
    chunks: list[str] = []
    buf = ""

    for piece in rendered:
        piece_len = len(piece)

        # Если текущий буфер пуст и кусок помещается - просто добавляем
        if not buf.strip() and piece_len <= limit:
            buf = piece
            continue

        # Пытаемся добавить кусок к буферу
        combined_len = len(buf) + len(piece) if buf else piece_len

        if combined_len <= limit:
            # Можно объединить - добавляем к буферу
            if buf:
                # Добавляем перенос строки между текстом и кодом для читаемости
                buf = f"{buf}\n{piece}"
            else:
                buf = piece
        else:
            # Не помещается - нужно разбить
            if buf.strip():
                # Сохраняем текущий буфер
                if buf.startswith("<pre><code>"):
                    # Это блок кода - отправляем как есть
                    chunks.append(buf)
                else:
                    # Это текст - разбиваем по необходимости
                    chunks.extend(_split_plain(buf, limit))
                buf = ""

            # Обрабатываем текущий кусок
            if piece.startswith("<pre><code>"):
                # Блок кода - проверяем размер
                if piece_len <= limit:
                    buf = piece
                else:
                    # Код слишком большой - нужно разбить по строкам
                    # Извлекаем код из HTML
                    code_match = re.search(r"<pre><code>(.*?)</code></pre>", piece, re.DOTALL)
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
                                    chunks.append(_render_code_html(code_buf.rstrip("\n")))
                                code_buf = line
                        if code_buf.strip():
                            buf = _render_code_html(code_buf.rstrip("\n"))
                    else:
                        # Fallback: отправляем как есть (будет ошибка, но лучше чем ничего)
                        chunks.append(piece)
            else:
                # Текст - разбиваем по необходимости
                chunks.extend(_split_plain(piece, limit))

    # Добавляем оставшийся буфер
    if buf.strip():
        if buf.startswith("<pre><code>"):
            chunks.append(buf)
        else:
            chunks.extend(_split_plain(buf, limit))

    # Telegram HTML dislikes completely empty messages.
    return [c for c in (c.strip() for c in chunks) if c]
