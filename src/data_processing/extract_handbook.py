#!/usr/bin/env python3
"""
Скрипт для извлечения текста из HTML файлов Яндекс Хендбука по Python.

Очищает от мусора и создаёт чанки для RAG системы.

Использование:
    uv run python -m src.data_processing.extract_handbook
    
    # Или напрямую
    uv run python src/data_processing/extract_handbook.py
"""

import json
import re
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from bs4 import BeautifulSoup

from src.data_processing import PROCESSED_DATA_DIR, RAW_DATA_DIR

# Входная и выходная директории
INPUT_DIR = RAW_DATA_DIR / "python"
OUTPUT_DIR = PROCESSED_DATA_DIR / "python"

# Паттерны для фильтрации ненужных секций и текстов
SKIP_FILE_PATTERNS = [
    r"chemu-vi-nauchilis",  # Обзорные статьи "Чему вы научились"
    r"prezhde-chem-nachat",  # Вводные статьи
    r"kak-rabotat-s-sistemoi",  # Инструкции по работе с системой
]

# Заголовки секций для удаления
SKIP_SECTION_HEADINGS = [
    "Ключевые вопросы параграфа",
    "Что вы узнаете",
    "Что будет в этом параграфе",
    "Чему вы научились",
    "Чему вы научитесь",
]

# Паттерны текста для удаления (начало параграфа)
SKIP_TEXT_PATTERNS = [
    r"^В этом параграфе (вы узнаете|мы научимся|мы рассмотрим|вы научитесь)",
    r"^В следующем параграфе",
    r"^В предыдущем параграфе",
    r"^Вот чему вы научились",
    r"^В этой главе вы",
    r"^Во (второй|третьей|четвёртой|пятой|шестой) главе вы",
]


def should_skip_file(filename: str) -> bool:
    """Проверяет, нужно ли пропустить файл."""
    for pattern in SKIP_FILE_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            return True
    return False


def should_skip_section(heading: str) -> bool:
    """Проверяет, нужно ли пропустить секцию по заголовку."""
    heading_lower = heading.lower().strip()
    for skip_heading in SKIP_SECTION_HEADINGS:
        if skip_heading.lower() in heading_lower:
            return True
    return False


def should_skip_text(text: str) -> bool:
    """Проверяет, нужно ли пропустить текст."""
    for pattern in SKIP_TEXT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def clean_text(text: str) -> str:
    """Очищает текст от лишних символов."""
    return " ".join(text.split())


def extract_code_block(pre_elem) -> Optional[str]:
    """Извлекает код из блока pre."""
    data_content = pre_elem.get("data-content", "")
    if data_content:
        try:
            return unquote(data_content).strip()
        except Exception:
            pass

    code_elem = pre_elem.find("code")
    if code_elem:
        lines = []
        for line in code_elem.get_text().split("\n"):
            cleaned = re.sub(r"^\d+", "", line, count=1)
            lines.append(cleaned)
        return "\n".join(lines).strip()

    return pre_elem.get_text(strip=True)


def extract_table_as_text(table) -> str:
    """Преобразует HTML таблицу в текстовый формат."""
    rows = []
    for tr in table.find_all("tr"):
        cells = [clean_text(cell.get_text(strip=True)) for cell in tr.find_all(["td", "th"])]
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows) if rows else ""


def extract_sections(content_div, soup) -> list[dict]:
    """Извлекает структурированные секции из контента."""
    sections = []
    current_section = None
    skip_until_next_heading = False

    # Обрабатываем таблицы
    table_placeholders = {}
    for i, table in enumerate(content_div.find_all("table")):
        placeholder = f"__TABLE_{i}__"
        table_placeholders[placeholder] = extract_table_as_text(table)
        new_tag = soup.new_tag("p")
        new_tag.string = placeholder
        table.replace_with(new_tag)

    for elem in content_div.find_all(["h2", "h3", "h4", "p", "ul", "ol", "pre", "blockquote", "details"]):
        if elem.name in ["h2", "h3"]:
            heading_text = elem.get_text(strip=True)

            if should_skip_section(heading_text):
                skip_until_next_heading = True
                continue

            skip_until_next_heading = False

            if current_section and current_section["content"]:
                sections.append(current_section)

            current_section = {"heading": heading_text, "level": int(elem.name[1]), "content": []}

        elif skip_until_next_heading:
            continue

        elif elem.name == "h4":
            heading_text = elem.get_text(strip=True)
            if current_section:
                current_section["content"].append({"type": "subheading", "text": heading_text})

        elif elem.name == "p":
            text = clean_text(elem.get_text(strip=True))
            if not text:
                continue

            if text in table_placeholders:
                if current_section:
                    current_section["content"].append({"type": "table", "text": table_placeholders[text]})
                continue

            if should_skip_text(text):
                continue

            if current_section:
                current_section["content"].append({"type": "paragraph", "text": text})
            else:
                current_section = {"heading": "Введение", "level": 2, "content": [{"type": "paragraph", "text": text}]}

        elif elem.name in ["ul", "ol"]:
            items = []
            for li in elem.find_all("li", recursive=False):
                item_text = clean_text(li.get_text(strip=True))
                if item_text and not should_skip_text(item_text):
                    items.append(item_text)

            if items and current_section:
                current_section["content"].append({"type": "list", "ordered": elem.name == "ol", "items": items})

        elif elem.name == "pre":
            code = extract_code_block(elem)
            if code and current_section:
                lang = "python"
                options = elem.get("data-options", "")
                if "langName" in options:
                    match = re.search(r'"langName":"(\w+)"', options)
                    if match:
                        lang = match.group(1).lower()

                current_section["content"].append({"type": "code", "language": lang, "text": code})

        elif elem.name == "blockquote":
            text = clean_text(elem.get_text(strip=True))
            if text and current_section and not should_skip_text(text):
                current_section["content"].append({"type": "note", "text": text})

        elif elem.name == "details":
            summary = elem.find("summary")
            if summary:
                question = clean_text(summary.get_text(strip=True))
                answer_div = elem.find("div", class_="yfm-cut-content")
                if answer_div:
                    answer = clean_text(answer_div.get_text(strip=True))
                    if current_section and question and answer:
                        current_section["content"].append({"type": "qa", "question": question, "answer": answer})

    if current_section and current_section["content"]:
        sections.append(current_section)

    return sections


def extract_text_from_html(html_path: Path) -> Optional[dict]:
    """Извлекает структурированный текст из HTML файла."""
    if should_skip_file(html_path.name):
        print(f"  ⏭️  Пропуск: {html_path.name}")
        return None

    with open(html_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    title_elem = soup.find("h1", class_="styles_title__Ae0WW")
    if not title_elem:
        title_elem = soup.find("title")
    title = title_elem.get_text(strip=True) if title_elem else html_path.stem
    title = re.sub(r"\s*-\s*Основы Python$", "", title)

    lead_elem = soup.find("div", class_="styles_lead__rZ3U4")
    description = ""
    if lead_elem:
        desc_text = lead_elem.get_text(strip=True)
        if not should_skip_text(desc_text):
            description = desc_text

    content_div = soup.find("div", id="wysiwyg-client-content")
    sections = []
    if content_div:
        sections = extract_sections(content_div, soup)

    if not sections:
        print(f"  ⚠️  Нет контента: {html_path.name}")
        return None

    return {"title": title, "description": description, "source_file": html_path.name, "sections": sections}


def format_for_rag(data: dict) -> str:
    """Форматирует извлеченные данные в текст для RAG."""
    lines = [f"# {data['title']}\n"]
    if data["description"]:
        lines.append(f"{data['description']}\n")
    lines.append("")

    for section in data["sections"]:
        level = "#" * (section["level"] + 1)
        lines.append(f"\n{level} {section['heading']}\n")

        for item in section["content"]:
            if item["type"] == "subheading":
                lines.append(f"\n#### {item['text']}\n")
            elif item["type"] == "paragraph":
                lines.append(f"\n{item['text']}\n")
            elif item["type"] == "list":
                for i, list_item in enumerate(item["items"], 1):
                    prefix = f"{i}." if item.get("ordered") else "-"
                    lines.append(f"{prefix} {list_item}")
                lines.append("")
            elif item["type"] == "code":
                lang = item.get("language", "python")
                lines.append(f"\n```{lang}")
                lines.append(item["text"])
                lines.append("```\n")
            elif item["type"] == "note":
                lines.append(f"\n> {item['text']}\n")
            elif item["type"] == "qa":
                lines.append(f"\n**Вопрос:** {item['question']}\n")
                lines.append(f"**Ответ:** {item['answer']}\n")
            elif item["type"] == "table":
                lines.append(f"\n{item['text']}\n")

    return "\n".join(lines)


def slugify(text: str) -> str:
    """Создаёт безопасное имя файла из текста."""
    text = text.lower().replace(" ", "_")
    safe_chars = "abcdefghijklmnopqrstuvwxyzабвгдежзийклмнопрстуфхцчшщъыьэюя0123456789_-"
    return "".join(c for c in text if c in safe_chars)[:50]


def save_for_rag(all_data: list[dict], output_dir: Path) -> None:
    """Сохраняет данные для RAG системы."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Полный текст
    full_text = []
    for data in all_data:
        full_text.append(format_for_rag(data))
        full_text.append("\n" + "=" * 80 + "\n")

    text_path = output_dir / "handbook_python.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full_text))
    print(f"✓ Полный текст: {text_path}")

    # 2. JSON
    json_path = output_dir / "handbook_python.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"✓ JSON: {json_path}")

    # 3. Чанки
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(exist_ok=True)

    chunk_idx = 0
    for data in all_data:
        for section in data["sections"]:
            chunk_idx += 1

            chunk_text = f"# {data['title']}\n\n## {section['heading']}\n\n"

            for item in section["content"]:
                if item["type"] == "paragraph":
                    chunk_text += f"{item['text']}\n\n"
                elif item["type"] == "subheading":
                    chunk_text += f"### {item['text']}\n\n"
                elif item["type"] == "list":
                    for i, li in enumerate(item["items"], 1):
                        prefix = f"{i}." if item.get("ordered") else "-"
                        chunk_text += f"{prefix} {li}\n"
                    chunk_text += "\n"
                elif item["type"] == "code":
                    lang = item.get("language", "python")
                    chunk_text += f"```{lang}\n{item['text']}\n```\n\n"
                elif item["type"] == "note":
                    chunk_text += f"> {item['text']}\n\n"
                elif item["type"] == "qa":
                    chunk_text += f"**Вопрос:** {item['question']}\n\n"
                    chunk_text += f"**Ответ:** {item['answer']}\n\n"
                elif item["type"] == "table":
                    chunk_text += f"{item['text']}\n\n"

            slug = slugify(section["heading"])
            chunk_path = chunks_dir / f"chunk_{chunk_idx:03d}_{slug}.txt"
            with open(chunk_path, "w", encoding="utf-8") as f:
                f.write(chunk_text.strip())

    print(f"✓ Чанков: {chunk_idx} в {chunks_dir}")


def main():
    """Основная функция извлечения."""
    print("=" * 60)
    print("🔍 Извлечение текста из HTML")
    print("=" * 60)
    print(f"📂 Вход: {INPUT_DIR}")
    print(f"📂 Выход: {OUTPUT_DIR}")

    if not INPUT_DIR.exists():
        print(f"\n❌ Директория не найдена: {INPUT_DIR}")
        print("   Сначала запустите: uv run python -m src.data_processing.download_handbook")
        return

    html_files = sorted(INPUT_DIR.glob("*.html"))
    print(f"📄 Найдено файлов: {len(html_files)}")

    all_data = []

    for html_file in html_files:
        print(f"\n📖 {html_file.name}")
        data = extract_text_from_html(html_file)

        if data:
            all_data.append(data)
            print(f"  ✓ Секций: {len(data['sections'])}")

    print(f"\n📊 Обработано статей: {len(all_data)}")

    print("\n💾 Сохранение...")
    save_for_rag(all_data, OUTPUT_DIR)

    print("\n" + "=" * 60)
    print("✅ Готово!")
    print("=" * 60)


if __name__ == "__main__":
    main()

