---
name: skill-creator
description: Create, audit, and optimize Antigravity skills using progressive disclosure, sharp trigger descriptions, and subagent evaluation. Use when building a new skill from scratch, updating or splitting an existing skill, or diagnosing why a skill fails to trigger or perform well.
---

# Antigravity Skill Creator

Build focused, progressive-disclosure skills tailored for Google Antigravity (`~/.gemini/config/skills/`, `.agents/skills/`, and `~/.gemini/config/skills.json`).

## 1. Choose the Right Customization Type First

| Need | Use | Location |
|---|---|---|
| Always-on invariants & behavioral posture | `AGENTS.md` | `~/.gemini/config/AGENTS.md` or `<repo>/AGENTS.md` |
| File-glob or domain-scoped constraints | Scoped Rule (`.md` + `trigger:`) | `~/.gemini/config/rules/` or `<repo>/.agents/rules/` |
| Reusable multi-step workflow / runbook | **Skill** (`SKILL.md` + helpers) | `~/.gemini/config/skills/<name>/` or `<repo>/.agents/skills/<name>/` |
| Deterministic safety or gating script | Lifecycle Hook | `~/.gemini/config/hooks.json` or `<repo>/.agents/hooks.json` |

If the content is only 5–10 static constraints with no procedural steps, write a Rule instead of a Skill.

## 2. Antigravity Skill Anatomy

```text
<skill-name>/
├── SKILL.md          # Required: YAML frontmatter + concise procedural instructions (<180 lines)
├── scripts/          # Optional: deterministic CLI helpers (run with --help first)
├── references/       # Optional: bulky docs loaded on demand
└── examples/         # Optional: concrete templates or sample outputs
```

### Frontmatter Contract

```yaml
---
name: my-skill-name
description: >-
  Third-person summary of what this skill does and exact trigger situations.
  Include keywords and file/task signals so the agent knows when to activate it.
---
```

- `name`: lowercase letters, digits, and single hyphens only (`^[a-z0-9-]+$`), **matching the parent directory name**.
- `description`: the primary triggering surface (always visible in the turn index). Write in third person, avoid angle brackets (`<`/`>`), keep under 1024 chars, and state both **what** it does and **when** to use it.

## 3. Authoring Principles (2026 Standards)

1. **Assume Model Competence — Document Gotchas**: Skip generic programming tutorials. Focus on exact decision trees, failure modes, non-obvious quirks, and verification steps.
2. **Progressive Disclosure**: Keep `SKILL.md` lean. Move reference tables, schemas, or multi-page guides into `references/` and link them explicitly with when-to-read guidance.
3. **Black-Box Scripts**: When bundling utilities under `scripts/`, instruct the agent to run `--help` first instead of reading script internals into context.
4. **Templates Over Prose**: Show exact output layouts or checklists rather than vague prose.
5. **No Global Duplication**: Do not repeat universal rules already enforced by `~/.gemini/config/AGENTS.md`.

## 4. Creation & Optimization Workflow

1. **Capture Intent & Edge Cases**: Clarify the concrete task, inputs/outputs, verification signal, and failure modes to prevent.
2. **Draft Skill Structure**: Write `SKILL.md` plus any deterministic `scripts/` or `references/`.
3. **Validate Structure**: Run the bundled validator before testing:
   ```bash
   python3 ~/.gemini/config/skills/skill-creator/scripts/quick_validate.py <skill-dir>
   # On Windows PowerShell:
   # py -3 "$env:USERPROFILE\.gemini\config\skills\skill-creator\scripts\quick_validate.py" <skill-dir>
   ```
4. **Evaluate with Subagents (`invoke_subagent`)**:
   - Design 2–4 realistic user prompts (including tricky edge cases and a near-miss negative prompt that should *not* trigger).
   - Run a **with-skill** subagent and (for major workflows) a **baseline** subagent via `invoke_subagent` to verify the skill actually improves quality/correctness without bloating output.
   - Check trigger clarity: if the agent skips the skill on realistic prompts, sharpen keywords and task triggers in `description`.
5. **Iterate & Verify**: Fix any gaps surfaced by evaluation, re-run `quick_validate.py`, and inform the user to start a new session (or run `/skills reload` in CLI) to load the updated skill index.
