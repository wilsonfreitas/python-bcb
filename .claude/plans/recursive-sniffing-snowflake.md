# Migrate from black + pycodestyle to ruff

## Context
The project currently uses **black** (formatter) and **pycodestyle** (linter) as separate tools. Ruff is a faster, unified replacement that handles both formatting and linting. This migration consolidates two tools into one, with faster execution and a single configuration surface.

## Changes

### 1. Update `pyproject.toml` dependencies
- **Remove** `black >= 22.8.0` and `pycodestyle >= 2.9.1` from `[dependency-groups] dev`
- **Add** `ruff >= 0.9.0` to `[dependency-groups] dev`

### 2. Add ruff configuration to `pyproject.toml`
Add the following sections:
```toml
[tool.ruff]
line-length = 88  # match black's default
target-version = "py310"

[tool.ruff.lint]
select = ["E", "W", "F"]  # pycodestyle errors/warnings + pyflakes
```

### 3. Update CI workflow — `.github/workflows/lint.yml`
Replace:
```yaml
- name: Check formatting
  run: uv run black --check bcb/ tests/
```
With:
```yaml
- name: Check formatting
  run: uv run ruff format --check bcb/ tests/
- name: Lint
  run: uv run ruff check bcb/ tests/
```

### 4. Update `CLAUDE.md`
Replace the linting/formatting commands:
```bash
uv run ruff check bcb/                  # lint with ruff
uv run ruff format bcb/                 # format with ruff
```

### 5. Run `ruff format` on the codebase
Run `uv run ruff format bcb/ tests/` to reformat with ruff (should produce no changes since ruff format is black-compatible by default, but verify).

### 6. Run `uv sync` to update lockfile
After dependency changes, run `uv sync` to regenerate `uv.lock`.

## Files to modify
- `pyproject.toml` — deps + ruff config
- `.github/workflows/lint.yml` — CI steps
- `CLAUDE.md` — documented commands

## Verification
1. `uv run ruff format --check bcb/ tests/` — passes with no changes
2. `uv run ruff check bcb/ tests/` — no lint errors
3. `uv run mypy bcb/` — still passes (unchanged)
4. `uv run pytest -m "not integration"` — all tests pass
