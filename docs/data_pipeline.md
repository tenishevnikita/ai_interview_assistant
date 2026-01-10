# Data Pipeline: Получение и обработка данных для RAG

Документация описывает процесс сбора, обработки данных и построения векторного индекса для AI-помощника по подготовке к собеседованиям.

## Оглавление

- [Источники данных](#источники-данных)
- [Скачивание данных](#скачивание-данных)
- [Извлечение текста из HTML](#извлечение-текста-из-html)
- [Структура чанков](#структура-чанков)
- [Построение FAISS индекса](#построение-faiss-индекса)
- [Использование Retriever](#использование-retriever)
- [Добавление новых данных](#добавление-новых-данных)

---

## Источники данных

### Яндекс Хендбук по Python
- **URL:** https://education.yandex.ru/handbook/python
- **Описание:** Бесплатный учебник по Python от Яндекс Образования
- **Темы:** Основы Python, коллекции, функции, ООП, работа с файлами, numpy, pandas, requests
- **Количество статей:** 27
- **Чанков:** 328

### Яндекс Хендбук по ML
- **URL:** https://education.yandex.ru/handbook/ml
- **Описание:** Машинное обучение — от базовых концепций до продвинутых алгоритмов
- **Темы:** Линейные модели, градиентный бустинг, нейронные сети, кластеризация, метрики
- **Количество статей:** 70
- **Чанков:** 816

### Яндекс Хендбук по CS (Введение в компьютерные науки)
- **URL:** https://education.yandex.ru/handbook/vvedenie-v-kompiuternie-nauki
- **Описание:** Фундаментальные основы информатики
- **Темы:** Системы счисления, логические операции, представление данных, архитектура компьютера
- **Количество статей:** 24
- **Чанков:** 132

### Яндекс Хендбук по C++
- **URL:** https://education.yandex.ru/handbook/cpp
- **Описание:** Современный C++ от базовых конструкций до продвинутых концепций
- **Темы:** Типы данных, контейнеры STL, классы, шаблоны, RAII, умные указатели
- **Количество статей:** 24
- **Чанков:** (не извлечены)

### Яндекс Хендбук по Алгоритмам
- **URL:** https://education.yandex.ru/handbook/algorithms
- **Описание:** Алгоритмы и структуры данных
- **Темы:** Графы, динамическое программирование, сортировки, бинарный поиск, жадные алгоритмы
- **Количество статей:** 53
- **Чанков:** (не извлечены)

### Яндекс Хендбук по Linux
- **URL:** https://education.yandex.ru/handbook/linux
- **Описание:** Основы работы с Linux и командной строкой
- **Темы:** Терминал, файловая система, навигация, потоки ввода/вывода, текстовые редакторы
- **Количество статей:** 19
- **Чанков:** (не извлечены)

### Яндекс Хендбук по Математике
- **URL:** https://education.yandex.ru/handbook/math
- **Описание:** Математика для программистов
- **Темы:** Линейная алгебра, дискретная математика, теория вероятностей, комбинаторика
- **Количество статей:** 43
- **Чанков:** (не извлечены)

---

## Скачивание данных

### Скрипты

Для каждого хендбука есть отдельный скрипт:

| Хендбук | Скрипт | Команда |
|---------|--------|---------|
| Python | `download_handbook.py` | `uv run python -m src.data_processing.download_handbook` |
| ML | `download_handbook_ml.py` | `uv run python -m src.data_processing.download_handbook_ml` |
| CS | `download_handbook_cs.py` | `uv run python -m src.data_processing.download_handbook_cs` |
| C++ | `download_handbook_cpp.py` | `uv run python -m src.data_processing.download_handbook_cpp` |
| Algorithms | `download_handbook_algo.py` | `uv run python -m src.data_processing.download_handbook_algo` |
| Linux | `download_handbook_linux.py` | `uv run python -m src.data_processing.download_handbook_linux` |
| Math | `download_handbook_math.py` | `uv run python -m src.data_processing.download_handbook_math` |

### Как работает скрипт

1. **Открывает главную страницу хендбука**
2. **Собирает ссылки на все главы** из оглавления (CSS: `ul.styles_book-contents__a6F2_ a`)
3. **Последовательно загружает каждую страницу** с рандомной задержкой (2-4 сек)
4. **Обрабатывает капчу** — если появляется SmartCaptcha, ждёт пока пользователь пройдёт её вручную
5. **Сохраняет полный HTML** страницы в `data/raw/handbook/{topic}/`

### Защита от блокировки

- Отключение флага `webdriver` в navigator
- Рандомные задержки между запросами
- Ручное прохождение капчи при необходимости

### Выходные файлы

```
data/raw/handbook/
├── python/           # 27 файлов
├── ml/               # 70 файлов
├── cs/               # 24 файла
├── cpp/              # 24 файла
├── algorithms/       # 53 файла
├── linux/            # 19 файлов
└── math/             # 43 файла
```

**Формат имени:** `{номер}_{slug-из-url}.html`

---

## Извлечение текста из HTML

### Скрипты

| Хендбук | Скрипт | Команда |
|---------|--------|---------|
| Python | `extract_handbook.py` | `uv run python -m src.data_processing.extract_handbook` |
| ML | `extract_handbook_ml.py` | `uv run python -m src.data_processing.extract_handbook_ml` |
| CS | `extract_handbook_cs.py` | `uv run python -m src.data_processing.extract_handbook_cs` |
| C++ | `extract_handbook_cpp.py` | `uv run python -m src.data_processing.extract_handbook_cpp` |
| Algorithms | `extract_handbook_algo.py` | `uv run python -m src.data_processing.extract_handbook_algo` |
| Linux | `extract_handbook_linux.py` | `uv run python -m src.data_processing.extract_handbook_linux` |
| Math | `extract_handbook_math.py` | `uv run python -m src.data_processing.extract_handbook_math` |

### Что делает скрипт

1. **Фильтрация файлов** — пропускает ненужные:
   - `chemu-vi-nauchilis` — обзорные статьи "Чему вы научились"
   - `prezhde-chem-nachat` — вводные статьи
   - `kak-rabotat-s-sistemoi` — инструкции по системе проверки

2. **Фильтрация секций** — удаляет из текста:
   - "Ключевые вопросы параграфа"
   - "Что вы узнаете / научитесь"
   - Фразы вида "В этом параграфе вы узнаете..."
   - "В следующем / предыдущем параграфе..."

3. **Извлечение контента**:
   - Заголовки (`h2`, `h3`, `h4`)
   - Параграфы текста
   - Блоки кода (с определением языка из `data-options`)
   - Списки (нумерованные и маркированные)
   - Таблицы
   - Цитаты и заметки (`blockquote`)
   - Q&A блоки (`details` → `summary`)

### Парсинг HTML

Используется BeautifulSoup4 с поиском ключевых элементов:

| Элемент | CSS Selector | Содержимое |
|---------|--------------|------------|
| Заголовок | `h1.styles_title__Ae0WW` | Название статьи |
| Описание | `div.styles_lead__rZ3U4` | Краткое описание |
| Контент | `div#wysiwyg-client-content` | Основной текст |
| Код | `pre.pre-code-lines[data-content]` | URL-encoded код |

### Выходные данные

```
data/handbook/
├── python/
│   ├── handbook_python.txt    # Полный текст
│   ├── handbook_python.json   # Структурированный JSON
│   └── chunks/                # 328 чанков
├── ml/
│   ├── handbook_ml.txt
│   ├── handbook_ml.json
│   └── chunks/                # 816 чанков
├── cs/
│   ├── handbook_cs.txt
│   ├── handbook_cs.json
│   └── chunks/                # 132 чанка
└── ... (другие хендбуки)
```

---

## Структура чанков

Каждый чанк — это одна секция (h2/h3) из статьи.

### Формат чанка

```markdown
# {Название статьи}

## {Название секции}

{Содержимое секции: текст, код, списки...}
```

### Пример чанка

**Файл:** `chunk_019_f-строки.txt`

```markdown
# 2.1 Ввод и вывод данных. Операции с числами, строками. Форматирование

## f-строки

С их помощью мы можем встроить переменные прямо внутрь строки...

```python
name = "Пользователь"
print(f"Добрый день, {name}.")
```

Можно не только вставлять переменные, но и выполнять операции...
```

### Метаданные чанка

При загрузке в FAISS каждый чанк получает metadata:

```python
{
    "source": "chunk_019_f-строки.txt",
    "title": "2.1 Ввод и вывод данных...",
    "chunk_id": "chunk_019_f-строки",
    "source_dir": "python"
}
```

---

## Построение FAISS индекса

### Скрипт: `src/data_processing/build_index.py`

```bash
# Базовое использование (все доступные хендбуки)
uv run python -m src.data_processing.build_index

# С тестовыми запросами
uv run python -m src.data_processing.build_index --test

# Указать директории вручную
uv run python -m src.data_processing.build_index \
    --chunks-dir data/handbook/python/chunks \
    --chunks-dir data/handbook/ml/chunks \
    --index-path data/my_index
```

### Автоматическое обнаружение хендбуков

Скрипт автоматически ищет чанки в следующих директориях:
- `data/handbook/python/chunks`
- `data/handbook/ml/chunks`
- `data/handbook/cs/chunks`
- `data/handbook/cpp/chunks`
- `data/handbook/algorithms/chunks`
- `data/handbook/linux/chunks`
- `data/handbook/math/chunks`

### Модель эмбеддингов

**Модель:** `intfloat/multilingual-e5-small`
- **Размерность:** 384
- **Размер:** ~500MB
- **Языки:** Multilingual (отлично работает с русским)
- **Лицензия:** MIT

**Альтернативы:**
| Модель | Размерность | Размер | Качество |
|--------|-------------|--------|----------|
| `intfloat/multilingual-e5-small` | 384 | ~500MB | Хорошее |
| `intfloat/multilingual-e5-base` | 768 | ~1GB | Лучше |
| `intfloat/multilingual-e5-large` | 1024 | ~2GB | Лучшее |

### Особенности E5 моделей

E5 модели требуют префиксы:
- **Для документов:** `passage: {текст}`
- **Для запросов:** `query: {текст}`

Это реализовано автоматически в `FAISSRetriever`.

### Структура индекса

```
data/faiss_index/
├── index.faiss    # Векторный индекс FAISS
└── index.pkl      # Метаданные документов
```

---

## Использование Retriever

### Базовое использование

```python
from src.vector_store import create_retriever

# Создание (автоматически загружает индекс)
retriever = create_retriever()

# Проверка готовности
print(f"Готов: {retriever.is_ready}")
print(f"Документов: {retriever.document_count}")

# Поиск
docs = retriever.retrieve("Что такое декораторы?", k=5)
for doc in docs:
    print(doc.metadata["title"])
    print(doc.page_content[:200])
```

### Поиск со scores

```python
results = retriever.retrieve_with_scores("lambda функции", k=3)
for doc, score in results:
    print(f"[{score:.3f}] {doc.metadata['title']}")
```

### Интеграция с RAG Engine

```python
from src.vector_store import create_retriever
from src.llm.rag_engine import RAGEngine
from src.llm.memory import MemoryStore

# Создаём компоненты
retriever = create_retriever()
memory = MemoryStore()

# RAG Engine с FAISS
engine = RAGEngine(memory=memory, retriever=retriever)

# Использование
answer = await engine.answer(
    chat_id=123,
    user_id=456,
    user_text="Как создать класс в Python?"
)
```

---

## Добавление новых данных

### 1. Скачать HTML файлы

Создайте скрипт по аналогии с существующими `download_handbook_*.py`:
- Укажите `OUTPUT_DIR = RAW_DATA_DIR / "{topic}"`
- Укажите `HANDBOOK_URL = "https://education.yandex.ru/handbook/{topic}"`

### 2. Создать скрипт извлечения

Скопируйте и адаптируйте `extract_handbook_*.py`:
- Обновите пути к директориям
- Настройте фильтры для ненужных секций (если отличаются)

### 3. Извлечь чанки

```bash
uv run python -m src.data_processing.extract_handbook_{topic}
```

### 4. Пересобрать индекс

Добавьте путь к новым чанкам в `build_index.py` (в `default_dirs`) и запустите:

```bash
uv run python -m src.data_processing.build_index --test
```

### Добавление документов в существующий индекс

```python
from pathlib import Path
from langchain_core.documents import Document
from src.vector_store import create_retriever

retriever = create_retriever()

# Новые документы
new_docs = [
    Document(
        page_content="passage: Содержимое нового документа...",
        metadata={"title": "Новый документ", "source": "manual"}
    )
]

# Добавляем
retriever.add_documents(new_docs)

# Сохраняем
retriever.save()
```

---

## Метрики и производительность

### Текущие показатели

| Метрика | Значение |
|---------|----------|
| Документов в индексе (python+ml+cs) | 1276 |
| Размер индекса | ~2-3MB |
| Время загрузки индекса | ~100ms |
| Время поиска (k=5) | ~10ms |
| Время индексации | ~1-2 мин |

### Качество поиска

Примеры запросов и релевантность:

| Запрос | Top-1 результат | Score |
|--------|-----------------|-------|
| "Что такое декораторы?" | 4.3 Рекурсия. Декораторы. Генераторы | 0.250 |
| "Как работает цикл for?" | 2.3 Циклы | 0.200 |
| "Как читать файлы?" | 3.5 Работа с файлами. JSON | 0.253 |
| "Наследование классов" | 5.2 Наследование | 0.280 |

> Чем ниже score, тем лучше (это расстояние, не similarity).

---

## Полный пайплайн

```bash
# 1. Скачать HTML (требует Chrome/Chromium)
uv run python -m src.data_processing.download_handbook      # Python
uv run python -m src.data_processing.download_handbook_ml   # ML
uv run python -m src.data_processing.download_handbook_cs   # CS
uv run python -m src.data_processing.download_handbook_cpp  # C++
uv run python -m src.data_processing.download_handbook_algo # Algorithms
uv run python -m src.data_processing.download_handbook_linux # Linux
uv run python -m src.data_processing.download_handbook_math  # Math

# 2. Извлечь текст и создать чанки
uv run python -m src.data_processing.extract_handbook      # Python
uv run python -m src.data_processing.extract_handbook_ml   # ML
uv run python -m src.data_processing.extract_handbook_cs   # CS
uv run python -m src.data_processing.extract_handbook_cpp  # C++
uv run python -m src.data_processing.extract_handbook_algo # Algorithms
uv run python -m src.data_processing.extract_handbook_linux # Linux
uv run python -m src.data_processing.extract_handbook_math  # Math

# 3. Построить FAISS индекс (все хендбуки)
uv run python -m src.data_processing.build_index --test
```

---

## Структура проекта

```
ai_interview_assistant/
├── data/
│   ├── raw/handbook/
│   │   ├── python/         # 27 HTML файлов
│   │   ├── ml/             # 70 HTML файлов
│   │   ├── cs/             # 24 HTML файла
│   │   ├── cpp/            # 24 HTML файла
│   │   ├── algorithms/     # 53 HTML файла
│   │   ├── linux/          # 19 HTML файлов
│   │   └── math/           # 43 HTML файла
│   ├── handbook/
│   │   ├── python/
│   │   │   ├── chunks/     # 328 чанков
│   │   │   ├── handbook_python.txt
│   │   │   └── handbook_python.json
│   │   ├── ml/
│   │   │   ├── chunks/     # 816 чанков
│   │   │   ├── handbook_ml.txt
│   │   │   └── handbook_ml.json
│   │   ├── cs/
│   │   │   ├── chunks/     # 132 чанка
│   │   │   ├── handbook_cs.txt
│   │   │   └── handbook_cs.json
│   │   └── ...             # Другие хендбуки (после извлечения)
│   └── faiss_index/
│       ├── index.faiss
│       └── index.pkl
├── src/
│   ├── data_processing/
│   │   ├── __init__.py              # Пути к данным
│   │   ├── download_handbook.py     # Python
│   │   ├── download_handbook_ml.py  # ML
│   │   ├── download_handbook_cs.py  # CS
│   │   ├── download_handbook_cpp.py # C++
│   │   ├── download_handbook_algo.py # Algorithms
│   │   ├── download_handbook_linux.py # Linux
│   │   ├── download_handbook_math.py  # Math
│   │   ├── extract_handbook.py      # Python
│   │   ├── extract_handbook_ml.py   # ML
│   │   ├── extract_handbook_cs.py   # CS
│   │   ├── extract_handbook_cpp.py  # C++
│   │   ├── extract_handbook_algo.py # Algorithms
│   │   ├── extract_handbook_linux.py # Linux
│   │   ├── extract_handbook_math.py  # Math
│   │   └── build_index.py           # Построение FAISS индекса
│   └── vector_store/
│       ├── __init__.py
│       └── faiss_store.py           # FAISS Retriever
└── docs/
    └── data_pipeline.md             # Эта документация
```

---

## Зависимости

```toml
# pyproject.toml
faiss-cpu = ">=1.9.0"
langchain-community = ">=0.3.0"
langchain-huggingface = ">=0.1.0"
sentence-transformers = ">=3.0.0"
beautifulsoup4 = ">=4.14.3"
selenium = ">=4.39.0"
```

---

## Troubleshooting

### Капча при скачивании

При запуске `download_handbook_*.py` может появиться SmartCaptcha.
Скрипт автоматически определит капчу и будет ждать — просто пройдите её вручную в открытом браузере.

### Индекс не загружается

```
⚠️ Не удалось загрузить индекс
```

**Решение:** Пересоберите индекс:
```bash
uv run python -m src.data_processing.build_index
```

### Пустые результаты поиска

**Возможные причины:**
1. Индекс пустой — запустите `build_index.py`
2. Нет чанков — запустите `extract_handbook_*.py`
3. Ошибка в запросе — проверьте что запрос на русском

### Медленная индексация

При первом запуске скачивается модель эмбеддингов (~500MB). 
Последующие запуски будут быстрее (модель кэшируется в `~/.cache/huggingface/`).

---

## Дальнейшее развитие

- [x] Добавить хендбук по ML
- [x] Добавить хендбук по CS
- [x] Скачать хендбуки: C++, Algorithms, Linux, Math
- [ ] Извлечь чанки из: C++, Algorithms, Linux, Math
- [ ] Добавить транскрипции лекций из `transcripts/`
- [ ] Hybrid search (BM25 + Vector)
- [ ] Reranker для улучшения качества
- [ ] Кэширование embeddings для инкрементальной индексации
