#!/usr/bin/env python3
"""Create an isolated git worktree with the standard symlinks.

Idempotent — returns the existing worktree path if it already exists.

Usage:
  worktree-add.py <branch> [--from <base>] [--name <override>]
  worktree-add.py --help

@author Samson Paul, samson.paul@experionglobal.com
"""
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
from common import banner, die, project_slug, repo_root, warn  # noqa: E402
from config_parse import list_config_keys, read_config_value  # noqa: E402

USAGE = """worktree-add — create a worktree with the standard symlinks

USAGE:
    worktree-add <branch> [--from <base>] [--name <override>]
    worktree-add --help

ARGS:
    <branch>          Branch to check out (created from <base> if it doesn't exist)
    --from <base>     Base branch (default: configured branch base)
    --name <override> Override the worktree directory name
                      (default: branch name with prefix stripped, slashes replaced)

EXIT:
    0  worktree created (or already existed) — path emitted on stdout
    1  branch base unresolved
    2  error

EXAMPLES:
    worktree-add PROJ-12345/foo
    # → /…/worktrees-MyRepo/PROJ-12345-foo

    worktree-add PROJ-12345/foo --from develop
    # (uses develop as base)

    worktree-add my-experiment --name my-experiment
    # (custom name override)"""

WT_LOG = os.path.join(tempfile.gettempdir(), "worktree-add-latest.log")
TYPE_PREFIXES = ("feature/", "fix/", "hotfix/", "epic/", "chore/", "release/", "demo/")


def git_text(args):
    result = subprocess.run(["git", *args], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    return result.stdout.strip(), result.returncode


def ref_exists(ref):
    return subprocess.run(["git", "show-ref", "--verify", "--quiet", ref],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def run_logged(args):
    with open(WT_LOG, "w") as log:
        return subprocess.run(["git", *args], stdout=log, stderr=subprocess.STDOUT).returncode


def dump_log():
    try:
        sys.stderr.write(open(WT_LOG, encoding="utf-8", errors="replace").read())
    except OSError:
        pass


def parse_args(argv):
    branch = base = name_override = ""
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--from":
            base = argv[i + 1] if i + 1 < len(argv) else ""; i += 2
        elif arg == "--name":
            name_override = argv[i + 1] if i + 1 < len(argv) else ""; i += 2
        elif arg in ("-h", "--help"):
            print(USAGE); sys.exit(0)
        elif arg.startswith("--"):
            die(f"unknown flag: {arg} (try --help)")
        elif not branch:
            branch = arg; i += 1
        else:
            die(f"unexpected extra arg: {arg}")
    return branch, base, name_override


def compute_name(branch, override):
    if override:
        return override
    if branch.startswith(TYPE_PREFIXES):
        return branch.split("/", 1)[1]
    if re.match(r"[A-Z].*-[0-9].*/", branch):
        return branch.replace("/", "-")
    if "/" in branch:
        return branch.split("/", 1)[1]
    return branch


def resolve_base(base):
    if base:
        return base
    base = read_config_value("Branch base")
    if not base:
        sym, rc = git_text(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
        if rc != 0 or not sym:
            die("could not resolve base branch — pass --from <base>", 1)
        base = sym
    return base[len("origin/"):] if base.startswith("origin/") else base


def create_worktree(wt_path, branch, base):
    if ref_exists(f"refs/heads/{branch}"):
        if run_logged(["worktree", "add", wt_path, branch]) != 0:
            dump_log(); die("git worktree add failed")
    elif subprocess.run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        if run_logged(["worktree", "add", wt_path, "-b", branch, f"origin/{branch}"]) != 0:
            dump_log(); die("git worktree add failed")
    else:
        if run_logged(["worktree", "add", wt_path, "-b", branch, base]) != 0:
            dump_log(); die(f"git worktree add (new branch from {base}) failed")


def _link_entry(link_target, target_in_wt, is_dir):
    """Create target_in_wt -> link_target. Real symlink first; on Windows, when
    that fails for lack of privilege (no Developer Mode, not elevated), fall
    back to a junction (directories) or a hard link (files) — neither needs
    admin rights or Developer Mode. Both still require the same local volume;
    a cross-volume target has no unprivileged option and this returns False,
    same as a plain symlink failure would.
    """
    try:
        os.symlink(link_target, target_in_wt, target_is_directory=is_dir)
        return True
    except OSError:
        if os.name != "nt":
            return False
    try:
        if is_dir:
            os.makedirs(link_target, exist_ok=True)
            return subprocess.run(["cmd", "/c", "mklink", "/J", target_in_wt, link_target],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
        os.link(link_target, target_in_wt)
        return True
    except OSError:
        return False


def link_symlinks(wt_path, main_repo):
    slug = project_slug()
    if not slug:
        die("project_slug failed")
    project_data_root = os.path.join(os.path.expanduser("~"), ".claude", "projects", slug)
    linked = skipped = failed = 0
    for entry in list_config_keys("Worktree Symlinks"):
        if not entry:
            continue
        is_dir = entry.startswith(".claude/")
        target_in_wt = os.path.join(wt_path, entry)
        if is_dir:
            link_target = os.path.join(project_data_root, entry[len(".claude/"):])
            os.makedirs(os.path.dirname(target_in_wt), exist_ok=True)
        else:
            link_target = os.path.join(main_repo, entry)
        if os.path.islink(target_in_wt) or os.path.exists(target_in_wt):
            skipped += 1
            continue
        if _link_entry(link_target, target_in_wt, is_dir):
            linked += 1
        else:
            warn(f"link failed: {entry} -> {link_target}")
            failed += 1
    return linked, skipped, failed


def main():
    banner()
    branch, base, name_override = parse_args(sys.argv[1:])
    if not branch:
        print(USAGE)
        sys.exit(2)

    base = resolve_base(base)
    name = compute_name(branch, name_override)

    main_repo = repo_root()
    if not main_repo:
        die("not in a git repo")
    parent_dir = os.path.join(os.path.dirname(main_repo), f"worktrees-{os.path.basename(main_repo)}")
    wt_path = os.path.join(parent_dir, name)

    listing, _ = git_text(["worktree", "list", "--porcelain"])
    if any(line == f"worktree {wt_path}" for line in listing.split("\n")):
        print(wt_path)
        warn(f"worktree already exists at {wt_path}")
        sys.exit(0)

    if subprocess.run(["git", "fetch", "origin"], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode != 0:
        warn("git fetch origin failed (continuing)")
    try:
        os.makedirs(parent_dir, exist_ok=True)
    except OSError:
        die(f"could not create {parent_dir}")

    create_worktree(wt_path, branch, base)
    linked, skipped, failed = link_symlinks(wt_path, main_repo)

    print(wt_path)
    suffix = f" failed={failed}" if failed > 0 else ""
    print(f"✓ worktree at {wt_path} (linked={linked} skipped={skipped}{suffix})", file=sys.stderr)


if __name__ == "__main__":
    main()
