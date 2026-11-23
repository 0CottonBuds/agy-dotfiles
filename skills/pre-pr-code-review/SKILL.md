---
name: pre-pr-code-review
description: >-
  Adversarial self-review workflow before committing or opening a PR. Use when finishing a
  feature, refactor, or bugfix, reviewing staged or unstaged diffs, or preparing a branch
  for commit or pull request.
---

# Pre-PR Self-Review

Inspect your actual diff critically before proposing a commit or PR.

## Step 1: Gather Exact Diff State

Run non-interactively in the target repo:
```bash
git status --short
git branch --show-current
git diff --stat
git diff
git diff --cached
```
If on `main` or `master`, flag it immediately and recommend creating a feature/fix branch before committing.

## Step 2: 6-Point Adversarial Audit

Inspect every changed hunk against these criteria:

1. **Scope & Surgical Discipline**: Does every changed line trace directly to the task? Any unrelated formatting churn, dead code left behind, or unrequested abstractions?
2. **Correctness & Edge Cases**: Are `null`/`None`, empty collections, boundary numbers, timezones, and error paths handled explicitly without silent fallbacks?
3. **Types & Contracts**: Any implicit `any`, `@ts-ignore`, unvalidated boundary payloads, or accidental API response key / schema renames?
4. **Security, Auth & Billing**: Are auth/permissions/quotas/pricing enforced server-side? Any `.env` files, secrets, tokens, or PII leaked into diffs or logs?
5. **Database & Performance**: Any N+1 queries, missing `select_related`/`selectinload`, destructive unguarded migrations, or unnecessary client re-renders?
6. **Tests & Verification**: Do tests actually exercise changed behavior (no mock tautologies), and were all checks re-run after the final edit?

## Step 3: Report & Fix

Present findings grouped strictly by severity (skip empty sections):
- **Blocker** *(must fix before commit)*: `<file:line>` — issue & fix
- **Should Fix** *(recommended)*: `<file:line>` — issue & fix
- **Nit** *(optional)*: `<file:line>` — minor observation

If blockers exist, ask/confirm before applying fixes, re-run verification after fixes, and once clean, present a ready-to-confirm **Conventional Commit** proposal (`git add <files>` + commit message).
