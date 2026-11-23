# agy-dotfiles

Portable, cross-platform (**Linux + Windows**) global Antigravity customization repository covering all 4 layers:

1. **Always-On Global Rules** (`AGENTS.md`) — behavioral posture, strict caution, surgical changes, goal-driven verification, and proactive Conventional Commit proposals.
2. **Modular Scoped Rules** (`rules/*.md`) — `glob` and `model_decision` rules for Python backends, TypeScript/React/RN, database migrations, security/billing, and git workflow.
3. **Global Skills** (`skills/` + `skills.json` + `community-skills.txt`) — bespoke engineering workflows (`systematic-debugging`, `tdd-and-verification`, `pre-pr-code-review`, `repo-customization-bootstrap`, `python-api-patterns`, `playwright-e2e`), promoted utility skills, and community skills installed via `npx skills`.
4. **Deterministic `PreToolUse` Safety Guard** (`hooks/safety_guard.py` + `hooks.template.json`) — blocks catastrophic Linux (`rm -rf /`, `curl | sh`) and Windows (`rd /s /q C:\`, `Remove-Item -Recurse -Force C:\`, `irm | iex`, `format C:`) commands and enforces `force_ask` on `git push`, destructive git/SQL/infra ops, and `.env`/credential access.

---

## Synced vs. Machine-Local

| Synced via this repo | Kept machine-local (never synced) |
|---|---|
| `AGENTS.md`, `rules/`, `skills/`, `skills.json`, `hooks/safety_guard.py` | `config.json` (machine hostname, sidecars, permission grants) |
| Generated OS-specific `hooks.json` (from `hooks.template.json`) | `mcp_config.json`, `plugins/`, `projects/`, `sidecars/` |
| Community skills manifest (`community-skills.txt`) | `~/.gemini/` auth tokens (`oauth_creds.json`, `.env`) |

---

## Quickstart

### Linux

```bash
git clone <your-private-repo-url> ~/Projects/agy-dotfiles
cd ~/Projects/agy-dotfiles
./install.sh
```

### Windows (PowerShell 5.1 or 7+)

```powershell
git clone <your-private-repo-url> "$env:USERPROFILE\Projects\agy-dotfiles"
cd "$env:USERPROFILE\Projects\agy-dotfiles"
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

> **Windows permissions note:** `install.ps1` uses directory **Junctions** for `rules`, `skills`, and `hooks`, and attempts **SymbolicLink -> NTFS HardLink -> Copy** for `AGENTS.md` and `skills.json`, so no Administrator prompt is needed when the repo is on the same NTFS drive (`C:\`).

---

## Installer Options

| Linux (`./install.sh`) | Windows (`.\install.ps1`) | Purpose |
|---|---|---|
| `--dry-run` | `-DryRun` | Preview actions without modifying files |
| `--skip-community` | `-SkipCommunity` | Skip `npx skills add` community skills sync |
| `--update-community` | `-UpdateCommunity` | Re-install/update community skills even if present |
| `--no-verify` | `-NoVerify` | Skip post-install validator and safety-guard test suite |

---

## Day-to-Day Sync Workflow

- **Linux & Windows (same drive / hardlinked):** Because `~/.gemini/config/{AGENTS.md,skills.json,rules,skills,hooks}` point directly into this repo, editing any rule or skill takes effect locally at once. Commit & push on one machine, then run `git pull` on the other.
- **When to re-run the installer:** Only if `hooks.template.json` or `community-skills.txt` changes, or if Windows had to use the cross-drive copy fallback for `AGENTS.md`/`skills.json`.
- **Verify anytime:**
  ```bash
  python3 ./skills/repo-customization-bootstrap/scripts/validate_customizations.py --target ~/.gemini/config
  python3 ./scripts/test_safety_guard.py
  ```

---

## Rollback

Before overwriting any pre-existing file or folder in `~/.gemini/config/`, the installers move it into a timestamped backup folder:

`~/.gemini/config/.backup-agy-dotfiles-YYYYMMDD-HHMMSS/` (or `%USERPROFILE%\.gemini\config\.backup-agy-dotfiles-YYYYMMDD-HHMMSS\`)

To restore, delete the created link/file in `~/.gemini/config/` and move the backed-up item back into place.
