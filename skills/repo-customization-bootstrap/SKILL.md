---
name: repo-customization-bootstrap
description: >-
  Scaffold, audit, and validate Antigravity customizations (AGENTS.md, .agents/rules/*.md,
  .agents/skills/*/SKILL.md, and .agents/hooks.json) for a repository or global config.
  Use when setting up a new repo for AI agents, migrating rules, or debugging why rules/skills
  fail to auto-discover.
---

# Repository Customization Bootstrap & Audit

Set up clean, discoverable project customizations without bloating context or duplicating global rules.

## Decision Tree

- **Auditing an existing repo or global config:** Run the validator script first (Step 1), then fix reported errors.
- **Bootstrapping a new repo:** Inspect stack manifests (`package.json`, `pyproject.toml`, `manage.py`, `Dockerfile`), author minimal files (Step 2), then run the validator (Step 3).

## Step 1: Run the Black-Box Validator First

Do not read the script source unless modifying it; check `--help` first and execute it:
```bash
python3 ~/.gemini/config/skills/repo-customization-bootstrap/scripts/validate_customizations.py --help
python3 ~/.gemini/config/skills/repo-customization-bootstrap/scripts/validate_customizations.py --target <repo-or-config-dir>
# On Windows PowerShell:
# py -3 "$env:USERPROFILE\.gemini\config\skills\repo-customization-bootstrap\scripts\validate_customizations.py" --target <repo-or-config-dir>
```

## Step 2: Authoring Rules & Layout Standards

1. **Root `<repo>/AGENTS.md` (Lean, <120 lines, <24 KB, NO frontmatter)**
   - Include ONLY project-specific facts: repo layout, exact build/test/lint/run commands, non-obvious architectural boundaries, and hard project invariants.
   - **Do NOT duplicate** universal coding rules already in `~/.gemini/config/AGENTS.md` or `~/.gemini/config/rules/`.
2. **Modular Rules (`<repo>/.agents/rules/*.md`)**
   - **Flat folder only**: Antigravity ignores nested subdirectories under `.agents/rules/` unless registered in `.agents/rules.json`.
   - **Mandatory YAML frontmatter** (missing or camelCase `trigger` causes silent discard):
     - `trigger: always_on | model_decision | glob | manual`
     - `description: "..."` (required for `model_decision`, recommended for all)
     - `globs: "*.ext, ..."` (required for `glob`; **always quote values starting with `*`** so YAML does not treat `*` as an alias anchor)
3. **Project Skills (`<repo>/.agents/skills/<name>/SKILL.md`)**
   - Create project-specific workflows only; reuse global skills (`systematic-debugging`, `tdd-and-verification`, `pytest-best-practices`, etc.) instead of copying them into repos.
   - Ensure `name` is lowercase kebab-case matching its parent directory name, with a clear third-person `description`.

## Step 3: Re-Validate & Summarize

Re-run `validate_customizations.py --target <repo-or-config-dir>` and verify exit code `0` before reporting completion.
