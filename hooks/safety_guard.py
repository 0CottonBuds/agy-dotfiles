#!/usr/bin/env python3
"""Deterministic PreToolUse safety gate for Antigravity global hooks (Linux & Windows)."""

from __future__ import annotations

import json
import os
import posixpath
import re
import sys
from pathlib import Path

ALLOWED_ENV_NAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.dist",
    ".env.local.example",
}

FILE_WRITE_TOOLS = {
    "write_file",
    "edit_file",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
}

GIT_CMD = r"\bgit\b(?:\s+-C\s+\S+|\s+--git-dir(?:=|\s+)\S+|\s+--work-tree(?:=|\s+)\S+)*"

DENY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?:^|[;&|]\s*|\|\|\s*|&&\s*)(?:sudo\s+)?rm(?=\s)"
            r"(?=[^\n;|&]*\s(?:-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|"
            r"-[a-zA-Z]*r\b[^\n;|&]*\s-[a-zA-Z]*f\b|-[a-zA-Z]*f\b[^\n;|&]*\s-[a-zA-Z]*r\b|"
            r"--recursive\b[^\n;|&]*--force\b|--force\b[^\n;|&]*--recursive\b))"
            r"[^\n;|&]*\s(?:/\*?|~/?|\$HOME/?|\$\{HOME\}/?|\.\./?)(?=\s|$|[;|&\"'])"
        ),
        "Blocked catastrophic recursive rm against root, home, or parent directory.",
    ),
    (
        re.compile(
            r"(?:^|[;&|]\s*|\|\|\s*|&&\s*)(?:rd|rmdir)\b(?=[^\n;|&]*/s\b)(?=[^\n;|&]*/q\b)"
            r"[^\n;|&]*\s(?:[A-Za-z]:\\\*?|%USERPROFILE%\\?|\$env:USERPROFILE\\?|\.\.\\?)(?=\s|$|[;|&\"'])",
            re.IGNORECASE,
        ),
        "Blocked catastrophic recursive Windows rd/rmdir against drive root, home, or parent directory.",
    ),
    (
        re.compile(
            r"(?:^|[;&|]\s*|\|\|\s*|&&\s*)(?:Remove-Item|ri|rm|del)\b(?=[^\n;|&]*-Rec(?:urse)?\b)"
            r"(?=[^\n;|&]*-Fo(?:rce)?\b)[^\n;|&]*\s"
            r"(?:[A-Za-z]:[\\/]\*?|/[*]?|~[\\/]?|\$HOME[\\/]?|\$env:USERPROFILE[\\/]?|%USERPROFILE%[\\/]?|\.\.[\\/]?)"
            r"(?=\s|$|[;|&\"'])",
            re.IGNORECASE,
        ),
        "Blocked catastrophic recursive PowerShell Remove-Item against root, home, or parent directory.",
    ),
    (
        re.compile(r"\bmkfs(?:\.[a-z0-9_]+)?\b"),
        "Blocked filesystem format command (mkfs).",
    ),
    (
        re.compile(
            r"(?:^|[;&|]\s*|\|\|\s*|&&\s*)format(?:\.com)?\s+[A-Za-z]:(?=\s|$|[;|&/])",
            re.IGNORECASE,
        ),
        "Blocked Windows disk format command.",
    ),
    (
        re.compile(r"\bdd\b[^\n;|&]*\bif=[^\n;|&]*\bof=/dev/"),
        "Blocked raw disk write via dd to /dev/.",
    ),
    (
        re.compile(r":\(\)\s*\{"),
        "Blocked shell fork bomb pattern.",
    ),
    (
        re.compile(r"\bchmod\b[^\n;|&]*\s-R\s+777\s+/(?:\s|$|[;|&])"),
        "Blocked recursive 777 permission change on root filesystem.",
    ),
    (
        re.compile(r"\b(?:curl|wget)\b[^\n|;]*\|\s*(?:env\s+|sudo\s+)?(?:ba|z|da)?sh\b"),
        "Blocked remote script pipe-to-shell (curl/wget | sh).",
    ),
    (
        re.compile(
            r"\b(?:irm|iwr|Invoke-RestMethod|Invoke-WebRequest)\b[^\n|;]*\|\s*(?:iex|Invoke-Expression)\b",
            re.IGNORECASE,
        ),
        "Blocked remote PowerShell download pipe-to-execute (irm/iwr | iex).",
    ),
]

FORCE_ASK_CMD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(rf"{GIT_CMD}\s+push\b"),
        "Git push always requires explicit confirmation.",
    ),
    (
        re.compile(rf"{GIT_CMD}\s+reset\b[^\n;|&]*--hard\b"),
        "Destructive git reset --hard requires confirmation.",
    ),
    (
        re.compile(rf"{GIT_CMD}\s+clean\b[^\n;|&]*(?:\s-[a-zA-Z]*f|\s--force\b)"),
        "Destructive git clean -f requires confirmation.",
    ),
    (
        re.compile(rf"{GIT_CMD}\s+branch\b[^\n;|&]*\s-D\b"),
        "Force-deleting a git branch (-D) requires confirmation.",
    ),
    (
        re.compile(rf"{GIT_CMD}\s+(?:checkout\s+--\s+\.|restore\s+\.)(?:\s|$|[;|&])"),
        "Discarding working tree changes with '.' requires confirmation.",
    ),
    (
        re.compile(rf"{GIT_CMD}\s+commit\b[^\n;|&]*--amend\b"),
        "Amending a git commit requires confirmation.",
    ),
    (
        re.compile(rf"{GIT_CMD}\s+rebase\b"),
        "Rebasing git history requires confirmation.",
    ),
    (
        re.compile(r"\b(?:DROP\s+(?:TABLE|DATABASE|SCHEMA)|TRUNCATE\s+TABLE)\b", re.IGNORECASE),
        "Destructive SQL DROP/TRUNCATE requires confirmation.",
    ),
    (
        re.compile(
            r"\b(?:terraform\s+destroy|docker\s+system\s+prune|docker\s+volume\s+(?:rm|prune)|"
            r"kubectl\s+delete|aws\s+s3\s+(?:rm|rb)|aws\s+rds\s+delete-)\b"
        ),
        "Destructive infrastructure/container command requires confirmation.",
    ),
    (
        re.compile(
            r"(?:~|\$HOME|\$\{HOME\}|/home/[^/\s]+|%USERPROFILE%|\$env:USERPROFILE|"
            r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s]+)[\\/]+\.(?:ssh[\\/]+id_|aws[\\/]+credentials)",
            re.IGNORECASE,
        ),
        "Accessing SSH keys or AWS credentials requires confirmation.",
    ),
    (
        re.compile(
            r"(?:\bprintenv\b|(?:^|[;&|]\s*|\|\|\s*|&&\s*)(?:sudo\s+)?env(?=\s*$|\s*[|;>&]))"
        ),
        "Dumping environment variables requires confirmation.",
    ),
    (
        re.compile(r"\b(?:Get-ChildItem|gci|ls|dir)\s+env:?(?=\s|$|[;|&])", re.IGNORECASE),
        "Dumping PowerShell environment variables requires confirmation.",
    ),
]

ENV_TOKEN_RE = re.compile(r"(?:^|[\s/\\\"'=])(\.env(?:\.[A-Za-z0-9_.-]+)?)(?=$|[\s\"';&|),:])")


def respond(decision: str, reason: str | None = None) -> int:
    payload: dict[str, str] = {"decision": decision}
    if reason:
        payload["reason"] = reason
    sys.stdout.write(json.dumps(payload) + "\n")
    return 0


def check_run_command(cmd: str) -> tuple[str, str | None]:
    for pattern, reason in DENY_PATTERNS:
        if pattern.search(cmd):
            return "deny", reason

    for pattern, reason in FORCE_ASK_CMD_PATTERNS:
        if pattern.search(cmd):
            return "force_ask", reason

    for match in ENV_TOKEN_RE.finditer(cmd):
        token = match.group(1)
        if token.lower() not in ALLOWED_ENV_NAMES:
            return "force_ask", f"Command references sensitive env file '{token}'; please confirm."

    return "allow", None


def check_file_write(raw_path: str) -> tuple[str, str | None]:
    if not raw_path:
        return "allow", None

    trimmed = raw_path.strip().rstrip("\\/")
    base = re.split(r"[\\/]", trimmed)[-1] if trimmed else ""
    base_lower = base.lower()

    if (base_lower == ".env" or base_lower.startswith(".env.")) and base_lower not in ALLOWED_ENV_NAMES:
        return "force_ask", f"Modifying sensitive env file '{base}' requires confirmation."

    if base_lower.endswith((".pem", ".key")) or ("credentials" in base_lower and base_lower.endswith(".json")):
        return "force_ask", f"Modifying key/credential file '{base}' requires confirmation."

    expanded_str = os.path.expandvars(os.path.expanduser(raw_path))
    expanded_path = Path(os.path.normpath(expanded_str))
    home = Path.home()
    ssh_dir = home / ".ssh"
    aws_dir = home / ".aws"
    gemini_cfg = home / ".gemini" / "config"
    hooks_dir = gemini_cfg / "hooks"

    if expanded_path == ssh_dir or ssh_dir in expanded_path.parents:
        return "force_ask", f"Modifying SSH directory file '{expanded_path}' requires confirmation."
    if expanded_path == aws_dir or aws_dir in expanded_path.parents:
        return "force_ask", f"Modifying AWS directory file '{expanded_path}' requires confirmation."
    if (
        expanded_path in {gemini_cfg / "config.json", gemini_cfg / "hooks.json"}
        or expanded_path == hooks_dir
        or hooks_dir in expanded_path.parents
    ):
        return "force_ask", f"Modifying global Antigravity security config '{expanded_path}' requires confirmation."

    # Cross-platform normalized forward-slash check (handles Windows paths even when tested on Linux)
    norm_fwd = posixpath.normpath(expanded_str.replace("\\", "/")).lower()
    if re.search(r"(?:^|/)\.(?:ssh|aws)(?:/|$)", norm_fwd):
        return "force_ask", f"Modifying SSH/AWS directory file '{raw_path}' requires confirmation."
    if re.search(r"(?:^|/)\.gemini/config/(?:config\.json|hooks\.json|hooks(?:/|$))", norm_fwd):
        return "force_ask", f"Modifying global Antigravity security config '{raw_path}' requires confirmation."

    return "allow", None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return respond("ask", "Safety guard could not parse tool payload; please confirm.")

    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}

    if tool_name == "run_command":
        decision, reason = check_run_command(str(args.get("CommandLine", "")))
        return respond(decision, reason)

    if tool_name in FILE_WRITE_TOOLS:
        raw_path = args.get("Path") or args.get("TargetFile") or args.get("FilePath") or ""
        decision, reason = check_file_write(str(raw_path))
        return respond(decision, reason)

    return respond("allow")


if __name__ == "__main__":
    raise SystemExit(main())
