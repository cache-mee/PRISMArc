#!/usr/bin/env python3
"""PreToolUse hook: Block Bash commands that trigger a human gate.

`.orchestration/policy/gates.json` defines consequential or irreversible
actions that require a human decision (merge, push-to-shared-branch, release,
destructive-operation, etc.). That policy is otherwise enforced only by prose
telling agents to "stop and ask" — nothing mechanically stops a matching
command from running. This hook is the mechanical backstop for the subset of
those gates that are reliably detectable from a shell command string alone:

  merge                    git merge / gh pr merge
  destructive-operation    git reset --hard, git clean -f[dx], git branch -D,
                           rm -rf / rm -fr (any order/combination of r+f flags),
                           except when confined to a disposable cache/build/
                           scratch path (node_modules, dist/, build/, .venv,
                           __pycache__, .next, coverage, /tmp/, .pytest_cache,
                           htmlcov) — routine cleanup, not irreversible loss
  push-to-shared-branch    git push naming main/master/develop as the target
  destructive-operation    force push (git push --force / --force-with-lease / -f)
  release                  git tag ... && git push ... (tag-then-push in one command)
  dependency-change        npm/pnpm/yarn install|add|remove <pkg>, pip install <pkg>
                           (not -r requirements.txt), poetry/uv/cargo/bundle add|remove

Deliberately narrow: this does not attempt to catch every gate in
gates.json (e.g. production-deploy, external-action, scope-expansion,
architecture-change require judgement a regex cannot supply) — only the
six patterns above.

Unlike `secret-leak-guard.py` (documented fail-open), this hook is
fail-closed: any unexpected internal error blocks the command rather than
letting it through silently, because this hook exists specifically to stop
irreversible actions.

No hardcoded project-specific values in this script.

@author Samson Paul, samson.paul@experionglobal.com
"""
import json
import re
import sys


GATES_POLICY_PATH = ".orchestration/policy/gates.json"


def _block(gate_id, snippet, extra=""):
    """Build the JSON block decision dict for a matched gate."""
    reason = (
        f"BLOCKED: this command matches gate `{gate_id}` in `{GATES_POLICY_PATH}`.\n\n"
        f"Triggering part of the command: {snippet}\n\n"
        f"This requires human approval per `{GATES_POLICY_PATH}` — a human must run "
        f"this command directly, not the agent."
    )
    if extra:
        reason += f"\n\n{extra}"
    return {"decision": "block", "reason": reason}


def _check_merge(command):
    if re.search(r"(^|[;&|]|\s)gh\s+pr\s+merge\b", command):
        m = re.search(r"gh\s+pr\s+merge[^;&|]*", command)
        return _block("merge", (m.group(0) if m else "gh pr merge").strip())
    if re.search(r"(^|[;&|]|\s)git\s+merge\b", command):
        m = re.search(r"git\s+merge[^;&|]*", command)
        return _block("merge", (m.group(0) if m else "git merge").strip())
    return None


# Disposable cache/build/scratch paths. An `rm -rf` confined to these is routine
# cleanup, not the irreversible loss of work the destructive-operation gate exists
# to catch — blocking it would just push agents toward a wall of pointless
# human approvals and erode the gate's signal. Matched as a substring of the
# rm command text, so `rm -rf ./node_modules` and `rm -rf /tmp/scratch-x` are
# both recognised as safe; `rm -rf B2B_BE/app` is not.
_SAFE_RM_SUBSTRINGS = (
    "node_modules", "dist/", "build/", ".venv", "venv/", "__pycache__",
    ".next", "coverage", "/tmp/", ".pytest_cache", "htmlcov",
)


def _check_destructive(command):
    # git reset --hard
    if re.search(r"git\s+reset\b[^;&|]*--hard\b", command):
        m = re.search(r"git\s+reset\b[^;&|]*--hard[^;&|]*", command)
        return _block("destructive-operation", (m.group(0) if m else "git reset --hard").strip())

    # git clean with any combination of f/d/x flags (long or short form)
    clean_match = re.search(r"git\s+clean\b[^;&|]*", command)
    if clean_match:
        clean_cmd = clean_match.group(0)
        has_force = re.search(r"(^|\s)-[a-zA-Z]*f[a-zA-Z]*(\s|$)", clean_cmd) or "--force" in clean_cmd
        has_d_or_x = (
            re.search(r"(^|\s)-[a-zA-Z]*[dx][a-zA-Z]*(\s|$)", clean_cmd)
            or "--force-recurse-dirs" in clean_cmd
        )
        # Plain `git clean -f` alone is already destructive (deletes untracked files).
        if has_force:
            return _block("destructive-operation", clean_cmd.strip())

    # git branch -D (force delete)
    if re.search(r"git\s+branch\b[^;&|]*(-D\b|--delete\s+--force|-d\s+-f\b)", command):
        m = re.search(r"git\s+branch\b[^;&|]*", command)
        return _block("destructive-operation", (m.group(0) if m else "git branch -D").strip())

    # rm with recursive + force flags, in any order, combined or separate
    for m in re.finditer(r"(^|[;&|]\s*|\s)((?:\\?)rm)\s+[^;&|\n]*", command):
        rm_cmd = m.group(0)
        tokens = re.findall(r"--?[A-Za-z-]+", rm_cmd)
        has_r = any(
            t in ("-r", "-R", "--recursive") or re.fullmatch(r"-[a-zA-Z]*[rR][a-zA-Z]*", t)
            for t in tokens
        )
        has_f = any(
            t == "--force" or re.fullmatch(r"-[a-zA-Z]*f[a-zA-Z]*", t)
            for t in tokens
        )
        if has_r and has_f:
            if any(s in rm_cmd for s in _SAFE_RM_SUBSTRINGS):
                continue
            return _block("destructive-operation", rm_cmd.strip())

    return None


def _check_push_shared_branch(command):
    push_matches = re.finditer(r"git\s+push\b[^;&|]*", command)
    for m in push_matches:
        push_cmd = m.group(0)
        # Match refs targeting main/master/develop: "origin main", "HEAD:main",
        # "origin main:main", etc. Word-boundary so "developer" etc. don't match.
        if re.search(r"(^|[\s:/])(main|master|develop)(\s|$)", push_cmd):
            return _block("push-to-shared-branch", push_cmd.strip())
    return None


def _check_force_push(command):
    push_matches = re.finditer(r"git\s+push\b[^;&|]*", command)
    for m in push_matches:
        push_cmd = m.group(0)
        tokens = re.findall(r"--?[A-Za-z-]+", push_cmd)
        if "--force" in tokens or "--force-with-lease" in tokens or "-f" in tokens:
            return _block("destructive-operation", push_cmd.strip(), extra="(force push)")
    return None


def _check_release(command):
    if re.search(r"git\s+tag\b", command) and re.search(r"git\s+push\b", command):
        return _block("release", command.strip())
    return None


def _check_dependency_change(command):
    m = re.search(r"(^|[;&|]\s*)(npm|pnpm|yarn)\s+(install|i|add|uninstall|remove)\s+(?!$)[^-\s][^;&|]*", command)
    if m:
        return _block("dependency-change", m.group(0).strip())
    m = re.search(r"(^|[;&|]\s*)pip\s+install\s+(?!.*(?:-r\s|--requirement\s))[^-\s][^;&|]*", command)
    if m:
        return _block("dependency-change", m.group(0).strip())
    m = re.search(r"(^|[;&|]\s*)(poetry|uv|cargo|bundle)\s+(add|remove)\b[^;&|]*", command)
    if m:
        return _block("dependency-change", m.group(0).strip())
    return None


CHECKS = (
    _check_merge,
    _check_destructive,
    _check_push_shared_branch,
    _check_force_push,
    _check_release,
    _check_dependency_change,
)


def evaluate(command):
    """Return a block decision dict if `command` trips a gate, else None."""
    for check in CHECKS:
        result = check(command)
        if result is not None:
            return result
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        json.dump(_block(
            "gate-guard-internal-error",
            "(unparseable hook input)",
            extra=f"BLOCKED: gate-guard hook could not parse its input and is failing "
                  f"closed rather than allowing an unchecked command through: {exc}",
        ), sys.stdout)
        return

    if data.get("tool_name") != "Bash":
        json.dump({}, sys.stdout)
        return

    command = data.get("tool_input", {}).get("command") or ""
    if not command:
        json.dump({}, sys.stdout)
        return

    decision = evaluate(command)
    json.dump(decision if decision else {}, sys.stdout)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - deliberate fail-closed catch-all
        json.dump({
            "decision": "block",
            "reason": (
                f"BLOCKED: gate-guard hook hit an internal error and is failing closed "
                f"rather than allowing an unchecked command through: {exc}"
            ),
        }, sys.stdout)
