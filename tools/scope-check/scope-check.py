#!/usr/bin/env python3
"""Fail if a single change touches both B2B_BE/ and B2B_FE/.

Enforces CLAUDE.md's "Repository layout" rule mechanically: a ticket that
touches both backend and frontend MUST be two bounded changes, never one that
reaches across both top-level folders. This is a check, not a fixer — it
reports, it does not move or edit files.

Usage:
  scope-check.py [--base <ref>] [--head <ref>]   diff base...head (default:
                                                  base = origin/HEAD's branch,
                                                  head = HEAD)
  scope-check.py --staged                        diff --cached (pre-commit use)
  scope-check.py --files <path> [<path> ...]      an explicit file list
  scope-check.py --help

EXIT:
  0  no violation (touches at most one of the two folders, or neither)
  1  violation — files under both B2B_BE/ and B2B_FE/ in the same change
  2  usage/error

@author Samson Paul, samson.paul@experionglobal.com
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
from common import banner, die  # noqa: E402

# The two authoritative top-level folders from CLAUDE.md's "Repository layout".
# Update here if that table ever changes.
BACKEND_PREFIX = "B2B_BE/"
FRONTEND_PREFIX = "B2B_FE/"

USAGE = """scope-check — fail if a change touches both B2B_BE/ and B2B_FE/

USAGE:
    scope-check.py [--base <ref>] [--head <ref>]
    scope-check.py --staged
    scope-check.py --files <path> [<path> ...]
    scope-check.py --help

ARGS:
    --base <ref>   Compare against this ref (default: origin/HEAD's branch)
    --head <ref>   Compare at this ref (default: HEAD)
    --staged       Check staged changes instead (git diff --cached)
    --files ...    Check an explicit file list instead of asking git

EXIT:
    0  no violation
    1  violation — files under both B2B_BE/ and B2B_FE/
    2  usage/error
"""


def _run_git(args):
    result = subprocess.run(["git", *args], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    return result.stdout, result.returncode


def resolve_default_base():
    out, rc = _run_git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
    if rc != 0 or not out.strip():
        die("could not resolve a default base branch — pass --base <ref>", 2)
    sym = out.strip()
    return sym[len("origin/"):] if sym.startswith("origin/") else sym


def diff_files(base, head):
    result = subprocess.run(["git", "diff", "--name-only", f"{base}...{head}"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        die(f"git diff {base}...{head} failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def staged_files():
    result = subprocess.run(["git", "diff", "--cached", "--name-only"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        die(f"git diff --cached failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def classify(files):
    backend = sorted(f for f in files if f.startswith(BACKEND_PREFIX))
    frontend = sorted(f for f in files if f.startswith(FRONTEND_PREFIX))
    return backend, frontend


def parse_args(argv):
    if not argv:
        return "diff", None, None, None
    if argv[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)
    if argv[0] == "--staged":
        if len(argv) > 1:
            die(f"unexpected extra arg(s) after --staged: {' '.join(argv[1:])}", 2)
        return "staged", None, None, None
    if argv[0] == "--files":
        files = argv[1:]
        if not files:
            die("--files requires at least one path", 2)
        return "files", None, None, files
    base = head = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--base":
            if i + 1 >= len(argv):
                die("--base requires a value", 2)
            base = argv[i + 1]; i += 2
        elif arg == "--head":
            if i + 1 >= len(argv):
                die("--head requires a value", 2)
            head = argv[i + 1]; i += 2
        else:
            die(f"unknown argument: {arg} (try --help)", 2)
    return "diff", base, head, None


def main():
    banner()
    mode, base, head, files = parse_args(sys.argv[1:])

    if mode == "files":
        touched = files
    elif mode == "staged":
        touched = staged_files()
    else:
        base = base or resolve_default_base()
        head = head or "HEAD"
        touched = diff_files(base, head)

    backend, frontend = classify(touched)

    if backend and frontend:
        print(f"FAIL scope-check ({len(backend)} backend + {len(frontend)} frontend file(s))")
        print("\nBackend files:")
        for f in backend:
            print(f"  {f}")
        print("\nFrontend files:")
        for f in frontend:
            print(f"  {f}")
        print("\nCLAUDE.md's Repository layout rule requires this to be two bounded "
              "changes, one per folder — not one change that reaches across both.")
        sys.exit(1)

    scope = "backend" if backend else "frontend" if frontend else "neither folder"
    print(f"PASS scope-check ({len(touched)} file(s) touched, {scope})")
    sys.exit(0)


if __name__ == "__main__":
    main()
