"""
FAISS Vector Store для RAG системы.

Использует sentence-transformers для эмбеддингов (бесплатно, работает локально).
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

if TYPE_CHECKING:
    from langchain_core.embeddings import Embeddings

# Путь к индексу по умолчанию
DEFAULT_INDEX_PATH = Path(__file__).parent.parent.parent / "data" / "faiss_index"

# Модель для эмбеддингов (multilingual, хорошо работает с русским)
DEFAULT_MODEL_NAME = "intfloat/multilingual-e5-small"


def get_embeddings(model_name: str = DEFAULT_MODEL_NAME) -> Embeddings:
    """
    Создаёт embeddings модель.
    
    Модели на выбор (от быстрой к точной):
    - intfloat/multilingual-e5-small (384 dim, ~500MB) - быстрая, хорошая для русского
    - intfloat/multilingual-e5-base (768 dim, ~1GB) - баланс
    - intfloat/multilingual-e5-large (1024 dim, ~2GB) - точная
    """
    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs={"device": "cpu"},  # или "cuda" если есть GPU
        encode_kwargs={"normalize_embeddings": True},
    )


class FAISSRetriever:
    """
    Retriever на основе FAISS.
    Реализует протокол Retriever из rag_engine.
    """
    
    def __init__(
        self,
        index_path: Path | str = DEFAULT_INDEX_PATH,
        embeddings: Embeddings | None = None,
    ):
        self._index_path = Path(index_path)
        self._embeddings = embeddings or get_embeddings()
        self._store: FAISS | None = None
        
        # Загружаем индекс если существует
        if self._index_path.exists():
            self._load()
    
    def _load(self) -> None:
        """Загружает индекс из файла."""
        try:
            self._store = FAISS.load_local(
                str(self._index_path),
                self._embeddings,
                allow_dangerous_deserialization=True,  # нужно для pickle
            )
            print(f"✓ FAISS индекс загружен из {self._index_path}")
        except Exception as e:
            print(f"⚠️ Не удалось загрузить индекс: {e}")
            self._store = None
    
    def save(self) -> None:
        """Сохраняет индекс в файл."""
        if self._store is None:
            raise ValueError("Нет индекса для сохранения")
        
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        self._store.save_local(str(self._index_path))
        print(f"✓ FAISS индекс сохранён в {self._index_path}")
    
    def add_documents(self, documents: list[Document]) -> None:
        """
        Добавляет документы в индекс.
        
        Args:
            documents: список LangChain Document с page_content и metadata
        """
        if not documents:
            return
        
        if self._store is None:
            # Создаём новый индекс
            self._store = FAISS.from_documents(documents, self._embeddings)
        else:
            # Добавляем в существующий
            self._store.add_documents(documents)
        
        print(f"✓ Добавлено {len(documents)} документов в индекс")
    
    def retrieve(self, question: str, k: int = 5) -> list[Document]:
        """
        Ищет релевантные документы по вопросу.
        
        Args:
            question: текст запроса
            k: количество результатов
            
        Returns:
            список Document с релевантным контентом
        """
        if self._store is None:
            return []
        
        # Для e5 моделей рекомендуется добавлять префикс "query: "
        query = f"query: {question}"
        
        try:
            docs = self._store.similarity_search(query, k=k)
            return docs
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return []
    
    def retrieve_with_scores(self, question: str, k: int = 5) -> list[tuple[Document, float]]:
        """
        Ищет документы и возвращает их вместе со scores.
        """
        if self._store is None:
            return []
        
        query = f"query: {question}"
        
        try:
            results = self._store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return []
    
    @property
    def is_ready(self) -> bool:
        """Проверяет, готов ли индекс к поиску."""
        return self._store is not None
    
    @property
    def document_count(self) -> int:
        """Возвращает количество документов в индексе."""
        if self._store is None:
            return 0
        return self._store.index.ntotal


def create_retriever(index_path: Path | str = DEFAULT_INDEX_PATH) -> FAISSRetriever:
    """
    Фабричная функция для создания retriever.
    Использовать в RAGEngine.
    """
    return FAISSRetriever(index_path=index_path)

