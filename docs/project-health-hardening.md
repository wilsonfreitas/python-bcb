# Project Health Hardening Runbook

This document keeps the project-health hardening workflow restartable after a
pause. GitHub issue #44 is the source of truth for current status.

## Source Of Truth

- Tracking issue: https://github.com/wilsonfreitas/python-bcb/issues/44
- Milestone: `Project health hardening`
- Coordination branch: `project-health-hardening`

## Branch Strategy

Do not work from `main` for this initiative.

Each implementation issue should use its own branch created from
`project-health-hardening`:

```bash
git switch project-health-hardening
git pull
git switch -c hardening/<issue-number>-<short-title>
```

Merge path:

```text
implementation branch -> project-health-hardening -> main
```

Target pull requests for implementation issues to `project-health-hardening`,
not `main`.

## Execution Order

Follow the order in issue #44 unless there is a concrete reason to reorder.

Recommended order:

1. Fix the deterministic integration failure.
2. Add or adjust tests around current behavior before broad refactors.
3. Centralize and normalize HTTP and OData error handling.
4. Harden OData query serialization.
5. Align sync and async behavior.
6. Improve validation and parsing resilience.
7. Clean docs and examples.
8. Raise CI, coverage, lint, and dependency gates last.

## Working An Issue

For each implementation issue:

1. Read issue #44 and the specific implementation issue.
2. Start from an up-to-date `project-health-hardening`.
3. Create a focused branch named `hardening/<issue-number>-<short-title>`.
4. Keep changes scoped to that issue.
5. Run the checks listed in the issue.
6. Push the branch and open a PR against `project-health-hardening`.
7. After merge, check off the item in issue #44.

## Default Checks

Run the targeted tests for the issue, then use the standard project checks:

```bash
uv run pytest -m "not integration"
uv run ruff check bcb/ tests/
uv run ruff format --check bcb/ tests/
uv run mypy bcb/
```

For integration-test issues, also run:

```bash
uv run pytest -m integration
```

For coverage-focused issues, also run:

```bash
uv run pytest --cov=bcb --cov-report=term-missing -m "not integration"
```

## Resume Prompt

Use this prompt after the project has been idle:

```text
Read issue #44 and start the next unchecked ticket. Work from
`project-health-hardening`, create a branch named
`hardening/<issue-number>-<short-title>`, keep the work scoped to that issue,
and target the PR back to `project-health-hardening`.
```
