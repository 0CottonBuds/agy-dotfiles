---
name: python-api-patterns
description: >-
  Implementation and review patterns for FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2
  and Django + DRF + PostgreSQL backends. Use when designing API endpoints, service layers,
  DB queries, migrations, or API tests in Python backend services.
---

# Python API & ORM Patterns

Decision-focused playbook for FastAPI and Django/DRF PostgreSQL services.

## Stack Selection

- **FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic**: Use Section 1.
- **Django + DRF + PostgreSQL**: Use Section 2.

---

## 1. FastAPI + SQLAlchemy 2.0 + Alembic

- **Thin Routers, Typed Services**:
  - Keep FastAPI route functions limited to dependency injection, auth/permission checks, calling a service function, and returning a Pydantic v2 `response_model`.
  - Validate inputs with dedicated `Create`/`Update` Pydantic schemas; never reuse ORM models as request/response schemas.
- **SQLAlchemy 2.0 Discipline**:
  - Use `Mapped[...]` and `mapped_column(...)` declarations; avoid legacy 1.x `Column()` or implicit lazy loading in async routes.
  - Eagerly load relationships via `selectinload(...)` or `joinedload(...)` to prevent N+1 queries and `MissingGreenlet` errors in async sessions.
  - Use `with session.begin():` (or explicit rollback on exception) for multi-write units of work.
- **Alembic Checklist**:
  1. Ensure every new model module is imported in `alembic/env.py` metadata before `--autogenerate`.
  2. Inspect the generated `upgrade()` and `downgrade()` diffs for unintended drops, constraint renames, or missing `server_default`s.
  3. Test `alembic upgrade head` -> `alembic downgrade -1` -> `alembic upgrade head` locally before finishing.
- **API Testing**: Prefer dependency overrides (`app.dependency_overrides`) for per-test rollback DB sessions via `TestClient` or `httpx.AsyncClient`; never mock away SQLAlchemy validation when testing persistence invariants.

---

## 2. Django + DRF + PostgreSQL

- **Serializer & View Boundaries**:
  - Put field/cross-field shape validation in DRF `Serializer` (`validate_<field>`, `validate`), and multi-model business transitions or external side effects in `services/` wrapped in `@transaction.atomic`.
  - Use `select_related()` for FK/OneToOne and `prefetch_related()` for reverse/M2M relations on list/detail querysets.
- **Cohort & Reporting Queries**:
  - Compute conversion, trial, and funnel metrics directly from authoritative PostgreSQL queries inside `transaction` / annotated querysets rather than stitching external billing API timelines.
- **Migrations & Compatibility**:
  - Check downstream clients and serializers before renaming DRF fields or JSON keys.
  - Run `./venv/bin/python manage.py makemigrations --check --dry-run` and targeted `manage.py test` (or `pytest`) after model/view changes.
