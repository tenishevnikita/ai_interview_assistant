.PHONY: lint format format-check test test-e2e install check help
.PHONY: extract-all extract-python extract-ml extract-cs extract-cpp extract-algo extract-linux extract-math
.PHONY: build-index build-index-test rebuild-index
.PHONY: eval-rewrite eval-rewrite-out eval-retrieval eval-retrieval-out eval-rag eval-rag-full eval-all debug-retrieval
.PHONY: test-metrics test-rag test-memory test-formatting test-all

# ============================================================================
# Установка и проверка кода
# ============================================================================

install:
	uv sync --all-groups

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

check: lint format-check test
	@echo "✅ All checks passed!"

# ============================================================================
# Тестирование
# ============================================================================

test:
	uv run pytest tests/ -v --ignore=tests/e2e

test-e2e:
	uv run pytest tests/e2e -v -m e2e

test-metrics:
	uv run pytest tests/test_metrics.py -v

test-rag:
	uv run pytest tests/test_rag_engine.py -v

test-memory:
	uv run pytest tests/test_memory.py -v

test-formatting:
	uv run pytest tests/test_formatting.py -v

test-all: test test-metrics test-rag test-memory test-formatting

# ============================================================================
# Сбор и обработка чанков
# ============================================================================

extract-python:
	uv run python -m src.data_processing.extract_handbook_python

extract-ml:
	uv run python -m src.data_processing.extract_handbook_ml

extract-cs:
	uv run python -m src.data_processing.extract_handbook_cs

extract-cpp:
	uv run python -m src.data_processing.extract_handbook_cpp

extract-algo:
	uv run python -m src.data_processing.extract_handbook_algo

extract-linux:
	uv run python -m src.data_processing.extract_handbook_linux

extract-math:
	uv run python -m src.data_processing.extract_handbook_math

extract-all: extract-python extract-ml extract-cs extract-cpp extract-algo extract-linux extract-math
	@echo "✅ Все чанки обработаны!"

# ============================================================================
# Построение FAISS индекса
# ============================================================================

build-index:
	uv run python -m src.data_processing.build_index

build-index-test:
	uv run python -m src.data_processing.build_index --test

# Полная пересборка: обработка всех чанков и построение индекса
rebuild-index: extract-all build-index
	@echo "✅ Индекс пересобран!"

# ============================================================================
# Оценка качества (метрики)
# ============================================================================

# Оценка rewrite (conversation eval)
eval-rewrite:
	uv run python -m src.eval.run_eval --dataset data/validation_conversation.jsonl

eval-rewrite-out:
	uv run python -m src.eval.run_eval --dataset data/validation_conversation.jsonl --out eval_rewrite_report.json

# Оценка ретривера (retrieval metrics)
eval-retrieval:
	uv run python -m src.eval.run_rag_eval \
		--retrieval-dataset data/validation_retrieval.jsonl \
		--index-path data/faiss_index

eval-retrieval-out:
	uv run python -m src.eval.run_rag_eval \
		--retrieval-dataset data/validation_retrieval.jsonl \
		--index-path data/faiss_index \
		--out eval_retrieval_report.json

# Полная оценка RAG системы (retrieval + end-to-end)
eval-rag:
	uv run python -m src.eval.run_rag_eval \
		--conversation-dataset data/validation_conversation.jsonl \
		--retrieval-dataset data/validation_retrieval.jsonl \
		--index-path data/faiss_index

eval-rag-full:
	uv run python -m src.eval.run_rag_eval \
		--conversation-dataset data/validation_conversation.jsonl \
		--retrieval-dataset data/validation_retrieval.jsonl \
		--index-path data/faiss_index \
		--judge-model mistral-small-latest \
		--out eval_rag_report.json

# Оценка всех метрик
eval-all: eval-rewrite eval-retrieval
	@echo "✅ Все метрики вычислены!"

debug-retrieval:
	uv run python -m src.eval.debug_retrieval

# ============================================================================
# Запуск бота
# ============================================================================

run-bot:
	uv run python -m src.bot.main

# ============================================================================
# Помощь
# ============================================================================

help:
	@echo "📚 AI Interview Assistant - Makefile Commands"
	@echo ""
	@echo "Установка и проверка:"
	@echo "  make install          - Установить зависимости"
	@echo "  make lint             - Проверить код линтером"
	@echo "  make format           - Отформатировать код"
	@echo "  make check            - Запустить все проверки (lint + format-check + test)"
	@echo ""
	@echo "Тестирование:"
	@echo "  make test             - Запустить unit тесты"
	@echo "  make test-e2e         - Запустить e2e тесты (требует MISTRAL_API_KEY)"
	@echo "  make test-metrics     - Тесты метрик"
	@echo "  make test-rag         - Тесты RAG engine"
	@echo "  make test-memory      - Тесты памяти"
	@echo "  make test-formatting  - Тесты форматирования"
	@echo "  make test-all         - Запустить все тесты"
	@echo ""
	@echo "Обработка данных:"
	@echo "  make extract-python   - Обработать Python handbook"
	@echo "  make extract-ml       - Обработать ML handbook"
	@echo "  make extract-cs       - Обработать CS handbook"
	@echo "  make extract-cpp      - Обработать C++ handbook"
	@echo "  make extract-algo     - Обработать Algorithms handbook"
	@echo "  make extract-linux    - Обработать Linux handbook"
	@echo "  make extract-math     - Обработать Math handbook"
	@echo "  make extract-all      - Обработать все handbooks"
	@echo ""
	@echo "Построение индекса:"
	@echo "  make build-index      - Построить FAISS индекс"
	@echo "  make build-index-test - Построить индекс и запустить тестовые запросы"
	@echo "  make rebuild-index    - Пересобрать все чанки и индекс"
	@echo ""
	@echo "Оценка качества:"
	@echo "  make eval-rewrite     - Оценить rewrite качество"
	@echo "  make eval-retrieval   - Оценить ретривер (Recall@k, MRR@k, etc.)"
	@echo "  make eval-rag         - Полная оценка RAG системы"
	@echo "  make eval-rag-full    - Полная оценка с LLM-as-judge"
	@echo "  make eval-all         - Запустить все оценки"
	@echo "  make debug-retrieval  - Диагностика проблемных кейсов ретривера"
	@echo ""
	@echo "Запуск бота:"
	@echo "  make run-bot        - Запустить бота"
	@echo ""
	@echo "Примеры использования:"
	@echo "  make rebuild-index && make eval-all    - Полная пересборка и оценка"
	@echo "  make test-all && make check            - Тесты и проверки"
	@echo "  make extract-python && make build-index - Обновить только Python и индекс"
