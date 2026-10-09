# Convenience targets. The real work lives in scripts/ (and in pyproject.toml).

.PHONY: lint format test zip bump

# Report style issues and check formatting, the way CI does. Default target.
lint:
	uv run ruff check
	uv run ruff format --check

# Fix whatever can be fixed, then reformat.
format:
	uv run ruff check --fix
	uv run ruff format

# Run the test suite. For the full matrix, use 'uv run nox'.
test:
	uv run pytest

# Build dist/weewx-sdr-<version>.zip for 'weectl extension install'.
zip:
	scripts/build_zip.py

# Write a new version into pyproject.toml, install.py and bin/user/core.py.
bump:
	@test -n "$(VERSION)" || { echo "usage: make bump VERSION=0.96b3"; exit 1; }
	scripts/bump_version.py $(VERSION)
