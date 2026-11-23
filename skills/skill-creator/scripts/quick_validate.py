#!/usr/bin/env python3
"""Quick stdlib-only validator for Antigravity SKILL.md bundles."""

from __future__ import annotations

import re
import sys
from pathlib import Path

MAX_NAME_LEN = 64
MAX_DESC_LEN = 1024
SOFT_LINE_LIMIT = 200
ALLOWED_KEYS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str] | tuple[None, str]:
    """Parse simple YAML key-value frontmatter (including > / | folded blocks) using stdlib only."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "Missing opening '---' YAML frontmatter delimiter"

    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
    if end_idx is None:
        return None, "Missing closing '---' YAML frontmatter delimiter"

    fm_lines = lines[1:end_idx]
    data: dict[str, str] = {}
    i = 0
    while i < len(fm_lines):
        raw = fm_lines[i]
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", raw)
        if not match:
            return None, f"Unsupported or malformed frontmatter line {i + 2}: {raw!r}"
        key, val = match.group(1), match.group(2).strip()
        if val in {">-", ">", "|-", "|", ""}:
            block: list[str] = []
            i += 1
            while i < len(fm_lines):
                nxt = fm_lines[i]
                if nxt.startswith((" ", "\t")):
                    block.append(nxt.strip())
                    i += 1
                elif not nxt.strip():
                    look = i + 1
                    while look < len(fm_lines) and not fm_lines[look].strip():
                        look += 1
                    if look < len(fm_lines) and fm_lines[look].startswith((" ", "\t")):
                        i += 1
                    else:
                        break
                else:
                    break
            data[key] = " ".join(part for part in block if part)
            continue
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        data[key] = val
        i += 1

    body = "\n".join(lines[end_idx + 1 :])
    return data, body


def validate_skill(skill_dir: Path) -> tuple[bool, list[str], list[str]]:
    """Return (is_valid, errors, warnings) for a skill directory."""
    errors: list[str] = []
    warnings: list[str] = []

    if not skill_dir.is_dir():
        return False, [f"Not a directory: {skill_dir}"], []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return False, [f"Missing SKILL.md in {skill_dir}"], []

    text = skill_md.read_text(encoding="utf-8")
    fm, body_or_err = parse_frontmatter(text)
    if fm is None:
        return False, [body_or_err], []

    unexpected = set(fm.keys()) - ALLOWED_KEYS
    if unexpected:
        warnings.append(f"Non-standard frontmatter keys: {', '.join(sorted(unexpected))}")

    name = fm.get("name", "").strip()
    if not name:
        errors.append("Missing required 'name' field in frontmatter")
    else:
        if not re.match(r"^[a-z0-9-]+$", name) or name.startswith("-") or name.endswith("-") or "--" in name:
            errors.append(f"Invalid skill name '{name}': must be lowercase kebab-case without leading/trailing/double hyphens")
        if len(name) > MAX_NAME_LEN:
            errors.append(f"Skill name '{name}' exceeds {MAX_NAME_LEN} chars")
        if name != skill_dir.name:
            errors.append(f"Skill name '{name}' does not match directory name '{skill_dir.name}'")

    desc = fm.get("description", "").strip()
    if not desc:
        errors.append("Missing required 'description' field in frontmatter")
    else:
        if "<" in desc or ">" in desc:
            errors.append("Description must not contain '<' or '>' angle brackets")
        if len(desc) > MAX_DESC_LEN:
            errors.append(f"Description exceeds {MAX_DESC_LEN} chars ({len(desc)})")

    if not body_or_err.strip():
        errors.append("SKILL.md body is empty")

    total_lines = len(text.splitlines())
    if total_lines > SOFT_LINE_LIMIT:
        warnings.append(
            f"SKILL.md is {total_lines} lines (>{SOFT_LINE_LIMIT}); consider moving bulky sections to references/"
        )

    return len(errors) == 0, errors, warnings


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] in {"-h", "--help"}:
        print("Usage: quick_validate.py <skill-directory>")
        return 0 if (len(sys.argv) == 2 and sys.argv[1] in {"-h", "--help"}) else 1

    target = Path(sys.argv[1]).expanduser().resolve()
    ok, errors, warnings = validate_skill(target)
    for warn in warnings:
        print(f"WARN: {warn}")
    for err in errors:
        print(f"ERROR: {err}")
    if ok:
        print(f"OK: {target.name} is valid.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
