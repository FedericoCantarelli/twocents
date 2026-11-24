.PHONY: test coverage format type

test:
	uv run pytest

coverage:
	uv run --with coverage coverage run -m pytest
	uv run --with coverage coverage report -m

format:
	uv run ruff format .

type:
	uv run ty check src
