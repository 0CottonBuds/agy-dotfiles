---
trigger: model_decision
description: "Apply whenever branching, using git worktrees, staging files, committing, pushing, opening PRs, or completing a verifiable unit of work in a git repo."
---

# Git Workflow & Commit Discipline

- **Branch & Worktree Isolation**: Never commit directly to `main` or `master`. Use dedicated feature/fix/refactor branches or `git worktree` for isolated or parallel work. If currently on `main`/`master` with work to commit, warn the user and propose creating a branch first.
- **Proactive Commit Handoff + Strict Confirmation**:
  - Never execute `git commit` or `git push` without explicit user confirmation.
  - Whenever a task or milestone is complete and verified in a git repo, **proactively** run `git status` and `git diff --stat`, propose the exact files to stage and an atomic **Conventional Commit** message (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:` with optional scope), and ask for quick confirmation to commit (and separately before pushing) so the user never has to ask.
- **Staging & Diff Hygiene**: Inspect `git diff` / `git diff --cached` before proposing a commit to ensure no `.env` files, credentials, debug prints, build artifacts, or unrelated edits are included.
- **History Safety**: Never force-push, `git reset --hard`, `git clean -fd`, or `--amend` pushed commits without explicit user approval.
