#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
SKIP_COMMUNITY=0
UPDATE_COMMUNITY=0
NO_VERIFY=0

usage() {
  cat <<'EOF'
Usage: ./install.sh [options]

Symlinks Antigravity global customizations from this repo into ~/.gemini/config/,
generates machine-local hooks.json from hooks.template.json, syncs community skills
into ~/.agents/skills/, and verifies the final setup.

Options:
  --dry-run           Show planned actions without modifying anything
  --skip-community    Skip installing community skills from community-skills.txt
  --update-community  Force re-install/update of community skills even if present
  --no-verify         Skip post-install validation and safety-guard test suite
  -h, --help          Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    --skip-community) SKIP_COMMUNITY=1 ;;
    --update-community) UPDATE_COMMUNITY=1 ;;
    --no-verify) NO_VERIFY=1 ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
CONFIG_DIR="${HOME}/.gemini/config"
AGENTS_SKILLS_DIR="${HOME}/.agents/skills"
BACKUP_DIR="${CONFIG_DIR}/.backup-agy-dotfiles-$(date +%Y%m%d-%H%M%S)"
BACKUP_USED=0

detect_python() {
  local cand
  for cand in /usr/bin/python3 "$(command -v python3 2>/dev/null || true)"; do
    if [[ -n "$cand" && -x "$cand" ]]; then
      if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
        echo "$cand"
        return 0
      fi
    fi
  done
  echo "ERROR: Python 3.9+ is required but was not found on PATH or /usr/bin/python3." >&2
  return 1
}

PYTHON_BIN="$(detect_python)"

ensure_backup_dir() {
  if [[ "$BACKUP_USED" -eq 0 ]]; then
    mkdir -p "$BACKUP_DIR"
    BACKUP_USED=1
  fi
}

realpath_py() {
  "$PYTHON_BIN" -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$1"
}

link_item() {
  local name="$1"
  local src="${REPO_DIR}/${name}"
  local dst="${CONFIG_DIR}/${name}"

  if [[ ! -e "$src" ]]; then
    echo "ERROR: Missing source item in repo: $src" >&2
    exit 1
  fi

  if [[ -L "$dst" ]]; then
    local cur_real src_real
    cur_real="$(realpath_py "$dst")"
    src_real="$(realpath_py "$src")"
    if [[ "$cur_real" == "$src_real" ]]; then
      echo "OK (already linked): $name"
      return 0
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] replace stale symlink: $dst -> $src"
      return 0
    fi
    rm -f "$dst"
    ln -s "$src" "$dst"
    echo "Relinked: $name -> $src"
    return 0
  fi

  if [[ -e "$dst" ]]; then
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] backup $dst -> $BACKUP_DIR/$name && ln -s $src $dst"
      return 0
    fi
    ensure_backup_dir
    mv "$dst" "${BACKUP_DIR}/${name}"
    ln -s "$src" "$dst"
    echo "Migrated (backed up old $name): $name -> $src"
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] ln -s $src $dst"
    return 0
  fi
  ln -s "$src" "$dst"
  echo "Linked: $name -> $src"
}

render_hooks_json() {
  local tpl="${REPO_DIR}/hooks.template.json"
  local dst="${CONFIG_DIR}/hooks.json"

  if [[ -f "$dst" && ! -L "$dst" ]]; then
    if "$PYTHON_BIN" -c '
import pathlib, sys
tpl = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
rendered = tpl.replace("{{PYTHON_CMD}}", sys.argv[2]).replace("{{HOOK_SCRIPT}}", "./hooks/safety_guard.py")
existing = pathlib.Path(sys.argv[3]).read_text(encoding="utf-8")
raise SystemExit(0 if existing == rendered else 1)
' "$tpl" "$PYTHON_BIN" "$dst" 2>/dev/null; then
      echo "OK (up to date): hooks.json"
      return 0
    fi
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] generate $dst (command: $PYTHON_BIN ./hooks/safety_guard.py)"
    return 0
  fi

  if [[ -L "$dst" ]]; then
    rm -f "$dst"
  elif [[ -e "$dst" ]]; then
    ensure_backup_dir
    mv "$dst" "${BACKUP_DIR}/hooks.json"
  fi

  local tmp
  tmp="$(mktemp "${CONFIG_DIR}/.hooks.json.XXXXXX")"
  "$PYTHON_BIN" -c '
import pathlib, sys
tpl = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
rendered = tpl.replace("{{PYTHON_CMD}}", sys.argv[2]).replace("{{HOOK_SCRIPT}}", "./hooks/safety_guard.py")
pathlib.Path(sys.argv[3]).write_text(rendered, encoding="utf-8")
' "$tpl" "$PYTHON_BIN" "$tmp"
  mv "$tmp" "$dst"
  echo "Generated: hooks.json ($PYTHON_BIN ./hooks/safety_guard.py)"
}

sync_community_skills() {
  local list_file="${REPO_DIR}/community-skills.txt"
  if [[ "$SKIP_COMMUNITY" -eq 1 ]]; then
    echo "Skipped community skills (--skip-community)."
    return 0
  fi
  if [[ ! -f "$list_file" ]]; then
    return 0
  fi

  local has_npx=0
  if command -v npx >/dev/null 2>&1; then
    has_npx=1
  fi

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"
    line="$(echo "$line" | xargs || true)"
    [[ -z "$line" ]] && continue

    local repo skill
    repo="${line%% *}"
    skill="${line#* }"

    if [[ -f "${AGENTS_SKILLS_DIR}/${skill}/SKILL.md" && "$UPDATE_COMMUNITY" -eq 0 ]]; then
      echo "OK (installed): ${skill}"
      continue
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "[dry-run] npx -y skills add $repo --skill $skill -g -y"
      continue
    fi

    if [[ "$has_npx" -eq 0 ]]; then
      echo "WARN: npx not found; install '$skill' manually later: npx -y skills add $repo --skill $skill -g -y" >&2
      continue
    fi

    npx -y skills add "$repo" --skill "$skill" -g -y
    # Ensure npx did not drop a symlink inside ~/.gemini/config/skills (which points to $REPO_DIR/skills)
    if [[ -L "${REPO_DIR}/skills/${skill}" ]]; then
      rm -f "${REPO_DIR}/skills/${skill}"
    fi
  done < "$list_file"
}

run_verification() {
  if [[ "$DRY_RUN" -eq 1 || "$NO_VERIFY" -eq 1 ]]; then
    return 0
  fi

  echo "=== Running post-install verification ==="
  "$PYTHON_BIN" "${CONFIG_DIR}/skills/repo-customization-bootstrap/scripts/validate_customizations.py" --target "$CONFIG_DIR"
  if [[ -d "${HOME}/.agents" ]]; then
    "$PYTHON_BIN" "${CONFIG_DIR}/skills/repo-customization-bootstrap/scripts/validate_customizations.py" --target "${HOME}/.agents"
  fi
  "$PYTHON_BIN" "${REPO_DIR}/scripts/test_safety_guard.py" --hook "${CONFIG_DIR}/hooks/safety_guard.py"
}

main() {
  echo "Repo:   $REPO_DIR"
  echo "Target: $CONFIG_DIR"
  echo "Python: $PYTHON_BIN"

  if [[ "$DRY_RUN" -eq 0 ]]; then
    mkdir -p "$CONFIG_DIR" "$AGENTS_SKILLS_DIR"
  else
    if [[ ! -d "$CONFIG_DIR" ]]; then
      echo "[dry-run] mkdir -p $CONFIG_DIR"
    fi
    if [[ ! -d "$AGENTS_SKILLS_DIR" ]]; then
      echo "[dry-run] mkdir -p $AGENTS_SKILLS_DIR"
    fi
  fi

  for item in AGENTS.md skills.json rules skills hooks; do
    link_item "$item"
  done

  render_hooks_json
  sync_community_skills
  run_verification

  echo ""
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Dry run complete. No files were modified."
  else
    echo "Linux Antigravity migration complete."
    if [[ "$BACKUP_USED" -eq 1 ]]; then
      echo "Backups saved to: $BACKUP_DIR"
    fi
    echo "Start a new Antigravity conversation (or run /skills reload in CLI) to apply changes."
  fi
}

main
