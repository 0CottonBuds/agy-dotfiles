#!/usr/bin/env python3
"""Stdlib-only validator for Antigravity customizations (global or workspace repo)."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from pathlib import Path

MAX_RULE_BYTES = 24_000
VALID_TRIGGERS = {"always_on", "model_decision", "glob", "manual"}


def parse_frontmatter(text: str) -> tuple[dict[str, tuple[str, str]] | None, str]:
    """Parse top-level YAML frontmatter keys. Returns ({key: (unquoted_val, raw_val)}, err)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "missing opening '---' YAML frontmatter"

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None, "missing closing '---' YAML frontmatter"

    fm_lines = lines[1:end_idx]
    data: dict[str, tuple[str, str]] = {}
    i = 0
    while i < len(fm_lines):
        raw = fm_lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", raw)
        if not match:
            return None, f"malformed frontmatter line {i + 2}: {raw!r}"
        key = match.group(1)
        raw_val = match.group(2).strip()
        if raw_val in {">-", ">", "|-", "|", ""}:
            block: list[str] = []
            i += 1
            while i < len(fm_lines):
                nxt = fm_lines[i]
                if nxt.startswith((" ", "\t")):
                    block.append(nxt.strip())
                    i += 1
                elif not nxt.strip():
                    # Consume blank lines only if indented continuation follows
                    look = i + 1
                    while look < len(fm_lines) and not fm_lines[look].strip():
                        look += 1
                    if look < len(fm_lines) and fm_lines[look].startswith((" ", "\t")):
                        i += 1
                    else:
                        break
                else:
                    break
            joined = " ".join(p for p in block if p)
            data[key] = (joined, raw_val)
            continue

        unquoted = raw_val
        if (raw_val.startswith('"') and raw_val.endswith('"')) or (
            raw_val.startswith("'") and raw_val.endswith("'")
        ):
            unquoted = raw_val[1:-1]
        data[key] = (unquoted, raw_val)
        i += 1

    return data, ""


def check_root_rule_docs(root: Path, errors: list[str], warnings: list[str]) -> int:
    """Validate AGENTS.md / GEMINI.md files under root and root/.agents/."""
    checked = 0
    candidates = [
        root / "AGENTS.md",
        root / "GEMINI.md",
        root / ".agents" / "AGENTS.md",
        root / ".agents" / "GEMINI.md",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        checked += 1
        size = path.stat().st_size
        if size > MAX_RULE_BYTES:
            errors.append(f"{path}: exceeds 24,000 byte cap ({size} bytes)")
        text = path.read_text(encoding="utf-8")
        if text.lstrip().startswith("---"):
            warnings.append(f"{path}: standalone AGENTS.md/GEMINI.md should not contain YAML frontmatter")
    return checked


def check_rules_dir(rules_dir: Path, errors: list[str], warnings: list[str]) -> int:
    """Validate modular rules inside rules/ or .agents/rules/."""
    if not rules_dir.is_dir():
        return 0
    checked = 0
    for child in sorted(rules_dir.iterdir()):
        if child.is_dir():
            warnings.append(
                f"{child}: nested directory under {rules_dir.name}/ is ignored unless registered in rules.json"
            )
            continue
        if child.suffix != ".md":
            continue
        checked += 1
        size = child.stat().st_size
        if size > MAX_RULE_BYTES:
            errors.append(f"{child}: exceeds 24,000 byte cap ({size} bytes)")
        text = child.read_text(encoding="utf-8")
        fm, err = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{child}: {err} (rules/*.md without valid frontmatter are silently discarded)")
            continue
        trigger = fm.get("trigger", ("", ""))[0].strip()
        if not trigger:
            errors.append(f"{child}: missing required 'trigger' in frontmatter")
        elif trigger not in VALID_TRIGGERS:
            errors.append(
                f"{child}: invalid trigger '{trigger}' (must be one of {sorted(VALID_TRIGGERS)})"
            )

        desc = fm.get("description", ("", ""))[0].strip()
        if trigger == "model_decision" and not desc:
            errors.append(f"{child}: trigger 'model_decision' requires non-empty 'description'")

        if trigger == "glob":
            glob_entry = fm.get("globs") or fm.get("glob")
            if not glob_entry or not glob_entry[0].strip():
                errors.append(f"{child}: trigger 'glob' requires non-empty 'globs' (or 'glob')")
            else:
                _, raw_glob = glob_entry
                if raw_glob.startswith("*") and not (
                    (raw_glob.startswith('"') and raw_glob.endswith('"'))
                    or (raw_glob.startswith("'") and raw_glob.endswith("'"))
                ):
                    errors.append(
                        f"{child}: unquoted glob pattern {raw_glob!r} starting with '*' is a YAML alias hazard; wrap in quotes"
                    )
    return checked


def check_skills_dir(skills_dir: Path, errors: list[str], warnings: list[str]) -> tuple[int, set[str]]:
    """Validate skills/*/SKILL.md under skills/ or .agents/skills/."""
    if not skills_dir.is_dir():
        return 0, set()
    checked = 0
    names: set[str] = set()
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        checked += 1
        entries = list(skill_dir.iterdir())
        if not entries:
            errors.append(f"{skill_dir}: empty skill directory")
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            errors.append(f"{skill_dir}: missing SKILL.md")
            continue
        text = skill_md.read_text(encoding="utf-8")
        fm, err = parse_frontmatter(text)
        if fm is None:
            errors.append(f"{skill_md}: {err}")
            continue
        desc = fm.get("description", ("", ""))[0].strip()
        if not desc:
            errors.append(f"{skill_md}: missing required 'description'")
        name = fm.get("name", ("", ""))[0].strip()
        effective_name = name or skill_dir.name
        if name:
            if not re.match(r"^[a-z0-9-]+$", name) or name.startswith("-") or name.endswith("-") or "--" in name:
                errors.append(f"{skill_md}: invalid kebab-case name '{name}'")
            if name != skill_dir.name:
                errors.append(f"{skill_md}: frontmatter name '{name}' does not match folder '{skill_dir.name}'")
        if effective_name in names:
            errors.append(f"{skill_md}: duplicate skill name '{effective_name}' in {skills_dir}")
        names.add(effective_name)
    return checked, names


def check_json_configs(config_root: Path, errors: list[str], warnings: list[str]) -> int:
    """Validate skills.json and hooks.json if present in config_root."""
    checked = 0
    skills_json = config_root / "skills.json"
    if skills_json.is_file():
        checked += 1
        try:
            data = json.loads(skills_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{skills_json}: invalid JSON: {exc}")
        else:
            for entry in data.get("entries", []) or []:
                raw_path = entry.get("path", "")
                if not raw_path:
                    errors.append(f"{skills_json}: entry missing 'path'")
                    continue
                resolved = Path(raw_path).expanduser()
                if not resolved.is_absolute():
                    resolved = (config_root.parent if config_root.name == ".agents" else config_root) / resolved
                if not resolved.exists():
                    errors.append(f"{skills_json}: referenced path does not exist: {raw_path} ({resolved})")

    hooks_json = config_root / "hooks.json"
    if hooks_json.is_file():
        checked += 1
        try:
            data = json.loads(hooks_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{hooks_json}: invalid JSON: {exc}")
        else:
            if not isinstance(data, dict):
                errors.append(f"{hooks_json}: top-level value must be a JSON object")
            else:
                for hook_name, spec in data.items():
                    if not isinstance(spec, dict):
                        errors.append(f"{hooks_json}: hook '{hook_name}' must be an object")
                        continue
                    for event in ("PreToolUse", "PostToolUse"):
                        for group in spec.get(event, []) or []:
                            for handler in group.get("hooks", []) or []:
                                _check_hook_cmd(hooks_json, hook_name, handler, errors)
                    for event in ("SessionStart", "PreInvocation", "PostInvocation", "Stop"):
                        for handler in spec.get(event, []) or []:
                            _check_hook_cmd(hooks_json, hook_name, handler, errors)
    return checked


def _check_hook_cmd(hooks_json: Path, hook_name: str, handler: dict, errors: list[str]) -> None:
    cmd = handler.get("command", "")
    if not cmd:
        errors.append(f"{hooks_json}: hook '{hook_name}' handler missing 'command'")
        return
    try:
        tokens = shlex.split(cmd, posix=(os.name != "nt"))
    except ValueError as exc:
        errors.append(f"{hooks_json}: hook '{hook_name}' invalid command quoting: {exc}")
        return
    script_exts = (".py", ".sh", ".ps1", ".bat", ".cmd")
    for raw_tok in tokens:
        tok = raw_tok.strip("\"'")
        norm_tok = tok.replace("\\", "/")
        is_rel_prefix = tok.startswith(("./", "../", ".\\", "..\\"))
        is_rel_script = norm_tok.lower().endswith(script_exts) and not Path(norm_tok).is_absolute()
        if is_rel_prefix or is_rel_script:
            target = (hooks_json.parent / norm_tok).resolve()
            if not target.exists():
                errors.append(f"{hooks_json}: hook '{hook_name}' references missing script {tok} ({target})")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Antigravity customizations (AGENTS.md, rules, skills, hooks.json, skills.json)."
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Path to customization root (e.g. ~/.gemini/config) or workspace repo (default: .)",
    )
    args = parser.parse_args()
    target = Path(args.target).expanduser().resolve()
    if not target.is_dir():
        print(f"ERROR: target is not a directory: {target}", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []

    root_docs = check_root_rule_docs(target, errors, warnings)
    rules_count = 0
    for rdir in (target / "rules", target / ".agents" / "rules"):
        rules_count += check_rules_dir(rdir, errors, warnings)

    skills_count = 0
    seen_skills: set[str] = set()
    for sdir in (target / "skills", target / ".agents" / "skills"):
        cnt, names = check_skills_dir(sdir, errors, warnings)
        skills_count += cnt
        overlap = seen_skills & names
        if overlap:
            errors.append(f"Duplicate skill names across {target}: {sorted(overlap)}")
        seen_skills |= names

    json_count = check_json_configs(target, errors, warnings)
    if (target / ".agents").is_dir():
        json_count += check_json_configs(target / ".agents", errors, warnings)

    for warn in warnings:
        print(f"WARN: {warn}")
    for err in errors:
        print(f"ERROR: {err}")

    print(
        f"Checked {target}: {root_docs} root doc(s), {rules_count} rule(s), "
        f"{skills_count} skill(s), {json_count} json config(s) — "
        f"{len(errors)} error(s), {len(warnings)} warning(s)."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
