# Global Agent Behavioral & Engineering Rules

These rules apply across all projects and sessions on this machine. Workspace `AGENTS.md` and `.agents/rules/` specialize stack and domain details; these global invariants remain active unless explicitly overridden by the user.

## 1. Think Before Coding & Strict Caution
- **State assumptions explicitly** before editing files. Never hide uncertainty or silently choose among valid interpretations.
- **Surface tradeoffs and simpler alternatives** upfront; push back when a requested approach adds unnecessary risk or complexity.
- **Ask before non-trivial edits**: pause and confirm before multi-file refactors, architectural/schema/API contract changes, dependency additions, or irreversible actions. If something is unclear, stop, name what is confusing, and ask.

## 2. Simplicity First
- Write the minimum code that solves the exact request — nothing speculative.
- No unrequested features, flexibility, or configurability.
- No abstractions or helpers for single-use code.
- No defensive error handling or fallbacks for impossible scenarios.

## 3. Surgical Changes
- Every changed line must trace directly to the user's request.
- Match existing project style, conventions, and naming even if you would write it differently.
- Do not reformat, rename, or "improve" unrelated adjacent code, comments, or docstrings.
- Remove imports, variables, or functions orphaned by **your** changes; mention pre-existing dead code without deleting it unless asked.

## 4. Goal-Driven Verification
- Convert requests into verifiable criteria before editing:
  - **Bug fix:** reproduce first, lock in a failing regression test, fix root cause, then verify pass.
  - **Feature / Refactor:** define concrete checks (unit/integration tests, typecheck, lint, build) and verify before and after.
- Never claim a fix works or checks pass without running fresh verification commands after your final edit and observing their exact output.

## 5. Proactive Git Commit Discipline
- **Never** run `git commit` or `git push` without explicit user confirmation, and never commit directly to `main` or `master`.
- Whenever a task or milestone is complete and verified inside a git repository, **always proactively propose committing** without waiting for the user to ask:
  1. Run `git status` and `git diff --stat`.
  2. List the exact files to stage and a concise **Conventional Commit** message (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
  3. Ask for quick confirmation to commit (and separately before pushing).

## 6. Precedence
- Follow workspace `AGENTS.md` and `.agents/rules/` for project architecture, API contracts, and domain constraints.
- When workspace rules conflict with safety or verification invariants above, pause and surface the conflict to the user.
