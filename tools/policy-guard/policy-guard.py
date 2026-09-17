#!/usr/bin/env python3
"""Mechanically enforce the backend/frontend scope boundary at write time.

`tools/scope-check` already enforces CLAUDE.md's Repository layout rule
(a change MUST NOT touch both `B2B_BE/` and `B2B_FE/`) — but only at commit
time, via the local pre-commit hook and CI. By then an agent may already have
written several cross-boundary files in one sitting. This tool closes that
gap: it runs `scope-check` against the working tree the moment a `Write` or
`Edit` tool call is about to add one more file to it, so a boundary violation
is caught at the first offending write, not at commit.

It does not duplicate `scope-check`'s logic — it shells out to it.

Bash-command gates (merge, push-to-shared-branch, destructive-operation,
release, dependency-change) are enforced separately by
`.claude/hooks/gate-guard.py`. Retry/no-progress/budget breakers are
enforced by `tools/breaker-check`. This tool's only job is pre-write scope.

Usage:
  policy-guard.py check-scope --files <path> [<path> ...]
  policy-guard.py hook            # Claude Code PreToolUse hook mode (stdin/stdout JSON)
  policy-guard.py --self-test
  policy-guard.py --help

EXIT:
  0  no violation
  1  blocked — scope violated
  2  usage/tool error

@author Samson Paul, samson.paul@experionglobal.com
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
from common import banner, die, repo_root  # noqa: E402

USAGE = """policy-guard — mechanical pre-write enforcement of the B2B_BE/B2B_FE scope boundary

USAGE:
    policy-guard.py check-scope --files <path> [<path> ...]
    policy-guard.py hook
    policy-guard.py --self-test
    policy-guard.py --help

EXIT:
    0  no violation
    1  blocked — scope violated
    2  usage/tool error

See tools/policy-guard/README.md for details and known limitations.
"""

# ---------------------------------------------------------------------------
# check-scope: delegate to the existing tools/scope-check, extended to
# whatever this session has already touched, so a violation is caught at the
# moment a second-folder file would be written — not just at commit time.
# ---------------------------------------------------------------------------

def _git(args, cwd):
    result = subprocess.run(["git", *args], cwd=cwd, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, text=True)
    return result.stdout, result.returncode


def _currently_touched_files(root):
    """Every path this working tree currently shows as changed (staged,
    unstaged, or untracked) — best-effort; returns [] on any git failure."""
    out, rc = _git(["status", "--porcelain"], root)
    if rc != 0:
        return []
    files = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:  # rename: "old -> new"
            path = path.split(" -> ", 1)[1]
        files.append(path.strip('"'))
    return files


def check_scope(root, candidate_files):
    """Run tools/scope-check --files against candidate_files plus everything
    already touched in the working tree. Returns (exit_code, stdout)."""
    scope_check = os.path.join(root, "tools", "scope-check", "scope-check.py")
    if not os.path.isfile(scope_check):
        return 0, "scope-check tool not found — skipping (fail-open)"
    full_list = sorted(set(_currently_touched_files(root)) | set(candidate_files))
    if not full_list:
        return 0, "PASS check-scope (nothing to check)"
    result = subprocess.run([sys.executable, scope_check, "--files", *full_list],
                             cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return result.returncode, result.stdout


def cmd_check_scope(args):
    banner()
    root = repo_root() or os.getcwd()
    rc, out = check_scope(root, args.files)
    print(out.strip())
    sys.exit(1 if rc == 1 else 0)


# ---------------------------------------------------------------------------
# hook: Claude Code PreToolUse entry point (stdin/stdout JSON), Write|Edit only
# ---------------------------------------------------------------------------

def run_hook():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        json.dump({}, sys.stdout)
        return

    tool_name = data.get("tool_name")
    if tool_name not in ("Write", "Edit"):
        json.dump({}, sys.stdout)
        return

    tool_input = data.get("tool_input") or {}
    target = tool_input.get("file_path")
    if not target:
        json.dump({}, sys.stdout)
        return

    root = repo_root()
    if not root:
        json.dump({}, sys.stdout)
        return

    rel = os.path.relpath(target, root)
    if rel.startswith(".."):
        json.dump({}, sys.stdout)  # outside the repo entirely — not this tool's concern
        return

    rc, out = check_scope(root, [rel])
    if rc == 1:
        json.dump({
            "decision": "block",
            "reason": (
                "BLOCKED by policy-guard (scope-check): writing this file would make "
                "the current change touch both B2B_BE/ and B2B_FE/, which "
                "CLAUDE.md's Repository layout rule forbids in a single change.\n\n"
                f"{out.strip()}\n\n"
                "Split this into two bounded changes, one per folder, or continue "
                "in a separate change for the other folder."
            ),
        }, sys.stdout)
        return
    json.dump({}, sys.stdout)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------

def _self_test():
    import tempfile
    failures = []

    def expect(label, cond):
        print(("ok   " if cond else "FAIL ") + label)
        if not cond:
            failures.append(label)

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init", "-q", tmp])
        subprocess.run(["git", "-C", tmp, "config", "user.email", "test@test"])
        subprocess.run(["git", "-C", tmp, "config", "user.name", "test"])
        os.makedirs(os.path.join(tmp, "tools", "scope-check"), exist_ok=True)
        real_root = repo_root() or os.getcwd()
        with open(os.path.join(real_root, "tools", "scope-check", "scope-check.py"), encoding="utf-8") as fh:
            src = fh.read()
        with open(os.path.join(tmp, "tools", "scope-check", "scope-check.py"), "w", encoding="utf-8") as fh:
            fh.write(src)
        os.makedirs(os.path.join(tmp, "tools", "_lib"), exist_ok=True)
        for name in ("common.py", "config_parse.py"):
            with open(os.path.join(real_root, "tools", "_lib", name), encoding="utf-8") as fh:
                lib_src = fh.read()
            with open(os.path.join(tmp, "tools", "_lib", name), "w", encoding="utf-8") as fh:
                fh.write(lib_src)

        os.makedirs(os.path.join(tmp, "B2B_BE"), exist_ok=True)
        with open(os.path.join(tmp, "B2B_BE", "existing.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        subprocess.run(["git", "-C", tmp, "add", "."])
        subprocess.run(["git", "-C", tmp, "commit", "-q", "-m", "init"])

        with open(os.path.join(tmp, "B2B_BE", "touched.py"), "w", encoding="utf-8") as fh:
            fh.write("x = 2\n")

        rc, out = check_scope(tmp, ["B2B_FE/new.tsx"])
        expect("check-scope blocks cross-folder write", rc == 1)
        rc2, _ = check_scope(tmp, ["B2B_BE/also_backend.py"])
        expect("check-scope allows same-folder write", rc2 == 0)

    print()
    if failures:
        print(f"FAIL self-test ({len(failures)} failure(s))")
        sys.exit(1)
    print("PASS self-test (all checks ok)")
    sys.exit(0)


# ---------------------------------------------------------------------------

def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)
    if argv[0] == "--self-test":
        _self_test()
        return
    if argv[0] == "hook":
        run_hook()
        return

    parser = argparse.ArgumentParser(add_help=False)
    sub = parser.add_subparsers(dest="subcommand")

    p_scope = sub.add_parser("check-scope")
    p_scope.add_argument("--files", nargs="+", required=True)

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        die("bad arguments (try --help)")

    if args.subcommand == "check-scope":
        cmd_check_scope(args)
    else:
        die("unknown subcommand (try --help)")


if __name__ == "__main__":
    main()
