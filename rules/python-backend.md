---
trigger: glob
globs: "*.py, pyproject.toml, requirements*.txt"
description: "Python backend coding standards for FastAPI, Django/DRF, SQLAlchemy 2.0, Pydantic v2, and pytest."
---

# Python Backend Standards

- **Strict Type Annotations**: Annotate all function parameters, return types, and service boundaries. Use Pydantic v2 schemas for API input/output validation and SQLAlchemy 2.0 typed `Mapped[...]` / `mapped_column(...)` models.
- **Explicit Error Handling**: Never use bare `except:` or silently swallow exceptions. Catch specific exception types, preserve context (`raise ... from exc`), and map domain errors cleanly at API boundaries.
- **Environment & Dependency Discipline**: Always execute Python tools and tests via the project's virtualenv (`./venv/bin/` or `.venv/bin/` on Linux/macOS, `.venv\Scripts\` on Windows, or `uv run` / `poetry run`). Never install packages into global/system Python without asking.
- **Layer Boundaries**: Keep HTTP views/routers thin; place business rules, external integrations, and multi-step transactions in service modules.
- **Query & Transaction Safety**: Avoid N+1 queries using `select_related` / `prefetch_related` (Django) or `selectinload` / `joinedload` (SQLAlchemy). Wrap multi-write state transitions in explicit database transactions (`transaction.atomic()` or session transactions).
- **Avoid Common Pitfalls**: Never use mutable default arguments (`def f(items=[])`); avoid mixing blocking I/O inside `async def` routes without offloading.
- **Verification**: Run the targeted `pytest` or `manage.py test` suite (and typechecker/linter if configured) after edits.
