.PHONY: lint format test test-e2e install check

install:
	uv sync --all-groups

lint:
	uv run ruff check .

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

test:
	uv run pytest tests/ -v --ignore=tests/e2e

test-e2e:
	uv run pytest tests/e2e -v -m e2e

check: lint format-check test
	@echo "✅ All checks passed!"

