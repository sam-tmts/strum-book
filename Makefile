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

# The whole of pathawks/Christmas-Songs, pinned, as a full book. The clone goes in the
# git-ignored collections/ folder: StrumBook only reads it and nothing is committed.
CHRISTMAS_REPO := https://github.com/pathawks/Christmas-Songs.git
CHRISTMAS_COMMIT := 263d5ce46d6569b6163b4a516874a203972b2b5b
CHRISTMAS_DIR := collections/christmas-songs

christmas:
	test -d $(CHRISTMAS_DIR) || git clone --quiet --no-checkout $(CHRISTMAS_REPO) $(CHRISTMAS_DIR)
	git -C $(CHRISTMAS_DIR) -c advice.detachedHead=false checkout --quiet $(CHRISTMAS_COMMIT)
	uv run --locked strumbook build $(CHRISTMAS_DIR) -o output/christmas-carols.pdf --title "Christmas Carols"
