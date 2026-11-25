# Run from the repository root. The first failing command stops make.
.PHONY: check test format build
check:
	uv run --locked pytest
	uv run --locked ruff check .
	uv run --locked ruff format --check .

test:
	uv run --locked pytest

format:
	uv run --locked ruff format .

build:
	uv build --no-sources
