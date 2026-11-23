---
name: playwright-e2e
description: >-
  Opaque-box Playwright E2E test authoring, debugging, and flake triage workflow. Use when
  writing browser tests, inspecting Playwright trace/HTML reports, fixing flaky selectors,
  or verifying web user flows end-to-end.
---

# Playwright E2E Workflow

Write resilient, opaque-box browser tests anchored to user-visible behavior rather than DOM internals.

## 1. Locator & Assertion Discipline

- **Preferred Locator Order**:
  1. `page.getByRole(...)` (accessible role + accessible name)
  2. `page.getByLabel(...)` / `page.getByPlaceholder(...)`
  3. `page.getByText(...)` (exact or scoped within a container)
  4. `page.getByTestId(...)` (only when semantic roles/text are ambiguous)
- **Avoid**: Brittle CSS class chains (`.btn > div:nth-child(2)`), Tailwind utility selectors, or XPath.
- **Web-First Assertions Only**: Always use auto-retrying assertions (`await expect(locator).toBeVisible()`, `toHaveText()`, `toHaveURL()`). Never use `page.waitForTimeout(...)`.

## 2. State, Auth & Isolation

- Reuse authenticated `storageState` via a setup project (`*.setup.ts`) instead of repeating UI logins in every spec.
- Keep specs independent and parallel-safe: seed isolated per-test data via API/helpers and never depend on execution order from an earlier `test()`.
- Wait for specific network/UI outcomes (`await page.waitForResponse(...)` or visible UI state), not arbitrary sleeps.

## 3. Debugging & Flake Triage Loop

1. Run the single failing spec in deterministic mode first:
   ```bash
   npx playwright test <path/to/spec.ts> --trace on
   ```
2. If it fails, inspect the trace/report (`npx playwright show-report` or trace zip) and server logs to distinguish:
   - **Real product bug** (backend 500, race condition, wrong UI state) -> fix root cause.
   - **Test race/locator defect** -> replace brittle locator or missing web-first assertion.
3. Run typecheck + smoke/target suite after final edits:
   ```bash
   npx tsc --noEmit && npx playwright test <smoke-or-target>
   ```
