# Run from the repository root. The first failing command stops make.
.PHONY: check test format build christmas
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

# The whole of pathawks/Christmas-Songs, pinned, as a full book. The StrumBook file clones
# it into the user cache: StrumBook only reads it and nothing is committed.
christmas:
	uv run --locked strumbook build books/christmas.strumbook.toml -o output/christmas-carols.pdf
