---
name: systematic-debugging
description: >-
  Disciplined 5-phase root-cause debugging workflow. Use whenever investigating bugs,
  test failures, regressions, 500 errors, flaky endpoints, or unexpected behavior—before
  making speculative code fixes.
---

# Systematic Debugging

Isolate the root cause with evidence before changing production code. Never patch symptoms blindly.

## 5-Phase Workflow

### 1. Reproduce & Observe
- Capture the exact failing command, HTTP status, traceback, log lines, or UI state.
- Confirm the failure is reproducible locally before forming hypotheses.
- Do not guess file paths, symbols, or errors from memory — read the actual traceback and source lines.

### 2. Trace & Form Hypothesis
- Trace execution from the failure boundary (UI/API/cron/DB) backward to where the invariant broke.
- Check recent `git log -n 10 --stat` or `git diff` if investigating a regression.
- State a **single falsifiable hypothesis** before touching code:
  - *"Fault occurs in `<file:line>` because `<cause>`, producing `<observed error>`."*

### 3. Lock In a Failing Regression Test
- Write the minimal unit, integration, or E2E test reproducing the bug (or verify an existing failing test captures the exact defect).
- Run the test and **observe it fail for the expected reason**.

### 4. Minimal Surgical Fix
- Implement the smallest fix addressing the root cause, not a downstream workaround.
- **Stop and ask the user** if the true fix requires altering an API contract, database schema, auth/billing logic, or cross-repo boundaries.

### 5. Verify & Propose Commit
- Re-run the regression test plus related module/integration tests and typechecks; confirm fresh exit code `0`.
- Inspect `git diff` to ensure no debug prints, temporary files, or unrelated edits remain.
- Propose staging and an atomic `fix:` Conventional Commit message.

## The 3-Strike Anti-Thrashing Rule

- **If 2 consecutive hypotheses/fixes fail:** **STOP editing immediately.**
- Summarize: (a) observed symptoms, (b) what each attempt changed and why it failed, (c) remaining unknowns.
- Ask the user for guidance or missing context before trying a third approach.
