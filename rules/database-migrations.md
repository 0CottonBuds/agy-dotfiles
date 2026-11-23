---
trigger: model_decision
description: "Apply whenever designing schemas, writing SQL, or creating/modifying PostgreSQL, Alembic, or Django migrations."
---

# Database & Migration Safety Rules

- **Inspect First**: Always read existing models, constraints, indexes, and recent migration history before generating or writing new migrations.
- **Expand-and-Contract for Breaking Changes**: Never drop columns/tables, rename active columns, or apply irreversible destructive alterations in a single step without explicit user confirmation. Prefer additive nullable/backfilled rollout phases first.
- **Live PostgreSQL Indexing**: Use `CREATE INDEX CONCURRENTLY` (outside a transaction block where required, e.g., `autocommit` / `atomic = False`) when indexing existing non-trivial tables to avoid write locks.
- **Reversibility**: Review auto-generated Alembic/Django migrations line-by-line before accepting them; verify both `upgrade`/`migrate` and `downgrade`/reverse paths.
- **Query Safety**: Always parameterize SQL inputs — never interpolate user data into raw SQL strings.
- **Environment Gate**: Never run migrations or destructive SQL against staging or production databases without explicit user approval.
