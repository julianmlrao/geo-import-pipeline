.PHONY: demo test lint
demo:
	./scripts/demo.sh
test:
	uv run pytest -q
lint:
	uv run ruff check . && uv run ruff format --check . && uv run mypy src
