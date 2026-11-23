---
name: tdd-and-verification
description: >-
  Test-driven development (Red-Green-Refactor) and strict verification workflow. Use when
  implementing new behavior, fixing bugs with tests, refactoring critical logic, or
  verifying changes before claiming completion.
---

# TDD & Verification Loop

Ensure every behavior change is backed by a real failing-then-passing test and fresh verification output.

## Red — Green — Refactor

1. **RED (Write Failing Test First)**
   - Write the smallest test expressing the desired behavior or reproducing the defect.
   - Run only that test and **confirm it fails for the expected reason** (assertion/behavior failure, not a syntax or fixture import error).

2. **GREEN (Minimal Passing Implementation)**
   - Write the minimum production code needed to make the failing test pass.
   - Re-run the test and confirm exit code `0`.

3. **REFACTOR (Clean Up While Green)**
   - Remove duplication you introduced and clarify names while keeping scope tight.
   - Re-run the full relevant test suite + typecheck/lint after the final edit.

## Anti-Mock-Tautology Checklist

Before accepting a new test as valid proof, verify it does NOT:
- Assert only that a mock was called with the values the test itself stubbed in.
- Mock out the very unit, query, validation rule, or serialization contract under test.
- Pass trivially when the production condition is inverted (if unsure, briefly verify failure).
- Silently relax assertions, skip failing tests, or swallow exceptions.

## Verification Gate (Iron Law)

Never state that tests pass, a build succeeds, or a bug is fixed unless:
1. You executed the exact check **after your final edit**.
2. You directly observed exit code `0` with no skipped/relaxed assertions on the changed scope.
3. Your final report states the exact command run and observed scope (including any subsets or mocked boundaries).

## Verification Checklist by Stack

- **Python (`pytest` / Django):** `pytest` on targeted + adjacent tests (and `mypy`/`ruff` if configured).
- **TypeScript / React / Next.js:** `tsc --noEmit` (or `npm run typecheck`), `npm run build`, and unit/E2E tests.
- **Playwright E2E:** Run targeted spec first, then smoke suite.
