#!/usr/bin/env python3
"""
Скрипт для построения FAISS индекса из чанков.

Использование:
    uv run python -m src.data_processing.build_index
    uv run python -m src.data_processing.build_index --test
    
    # Или напрямую
    uv run python src/data_processing/build_index.py --test
"""

import argparse
import sys
from pathlib import Path

from langchain_core.documents import Document

from src.data_processing import FAISS_INDEX_DIR, PROCESSED_DATA_DIR
from src.vector_store.faiss_store import FAISSRetriever, get_embeddings


def load_chunks_from_directory(chunks_dir: Path) -> list[Document]:
    """Загружает чанки из директории с текстовыми файлами."""
    documents = []

    if not chunks_dir.exists():
        print(f"❌ Директория не найдена: {chunks_dir}")
        return documents

    txt_files = sorted(chunks_dir.glob("*.txt"))

    if not txt_files:
        print(f"⚠️ Нет .txt файлов в {chunks_dir}")
        return documents

    print(f"📂 {chunks_dir}")
    print(f"   Файлов: {len(txt_files)}")

    for txt_file in txt_files:
        try:
            content = txt_file.read_text(encoding="utf-8").strip()

            if not content:
                continue

            lines = content.split("\n")
            title = lines[0].lstrip("# ").strip() if lines else txt_file.stem

            # Для e5 моделей добавляем префикс "passage: "
            prefixed_content = f"passage: {content}"

            doc = Document(
                page_content=prefixed_content,
                metadata={
                    "source": str(txt_file.name),
                    "title": title,
                    "chunk_id": txt_file.stem,
                    "source_dir": str(chunks_dir.name),
                },
            )
            documents.append(doc)

        except Exception as e:
            print(f"⚠️ Ошибка чтения {txt_file.name}: {e}")
            continue

    print(f"   Загружено: {len(documents)}")
    return documents


def build_index(
    chunks_dirs: list[Path],
    index_path: Path,
    model_name: str = "intfloat/multilingual-e5-small",
) -> FAISSRetriever:
    """Строит FAISS индекс из нескольких директорий."""
    print("\n🔧 Создание FAISS индекса")
    print(f"📦 Модель: {model_name}")
    print("⏳ Загрузка модели эмбеддингов...")

    embeddings = get_embeddings(model_name)

    all_documents = []
    for chunks_dir in chunks_dirs:
        docs = load_chunks_from_directory(chunks_dir)
        all_documents.extend(docs)

    if not all_documents:
        print("❌ Нет документов для индексации")
        sys.exit(1)

    print(f"\n📊 Всего документов: {len(all_documents)}")
    print("⏳ Создание эмбеддингов...")

    retriever = FAISSRetriever(index_path=index_path, embeddings=embeddings)
    retriever.add_documents(all_documents)
    retriever.save()

    print(f"\n✅ Индекс создан!")
    print(f"   Документов: {retriever.document_count}")
    print(f"   Путь: {index_path}")

    return retriever


def test_search(retriever: FAISSRetriever, queries: list[str]) -> None:
    """Тестирует поиск по индексу."""
    print("\n🔍 Тестовый поиск:")
    print("-" * 60)

    for query in queries:
        print(f"\n❓ {query}")
        results = retriever.retrieve_with_scores(query, k=3)

        if not results:
            print("   (нет результатов)")
            continue

        for i, (doc, score) in enumerate(results, 1):
            title = doc.metadata.get("title", "?")
            content = doc.page_content.replace("passage: ", "")[:100]
            print(f"   [{i}] {score:.3f} | {title}")
            print(f"       {content}...")


def main():
    parser = argparse.ArgumentParser(description="Построение FAISS индекса")
    parser.add_argument(
        "--chunks-dir",
        type=Path,
        action="append",
        dest="chunks_dirs",
        help="Директория с чанками (можно несколько)",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=FAISS_INDEX_DIR,
        help=f"Путь для индекса (default: {FAISS_INDEX_DIR})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="intfloat/multilingual-e5-small",
        help="Модель эмбеддингов",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Запустить тестовые запросы",
    )

    args = parser.parse_args()

    # Директории по умолчанию
    if not args.chunks_dirs:
        default_dirs = [
            PROCESSED_DATA_DIR / "python" / "chunks",
        ]
        args.chunks_dirs = [d for d in default_dirs if d.exists()]

    if not args.chunks_dirs:
        print("❌ Не найдены директории с чанками")
        print("   Сначала запустите: uv run python -m src.data_processing.extract_handbook")
        sys.exit(1)

    print("=" * 60)
    print("🚀 FAISS Index Builder")
    print("=" * 60)

    retriever = build_index(
        chunks_dirs=args.chunks_dirs,
        index_path=args.index_path,
        model_name=args.model,
    )

    if args.test:
        test_queries = [
            "Что такое декораторы в Python?",
            "Как работает цикл for?",
            "Что такое list comprehension?",
            "Как читать файлы в Python?",
            "Объясни наследование классов",
        ]
        test_search(retriever, test_queries)

    print("\n" + "=" * 60)
    print("✅ Готово!")
    print("=" * 60)


if __name__ == "__main__":
    main()

