"""Generic helpers used by every Python tool in tools/.

Pure functions, no project-specific knowledge. Standard library only,
cross-OS (Windows, macOS, Linux).

Exports:
  repo_root()                  -> str | None   git repo root (honours CLAUDE_PROJECT_DIR)
  project_slug()               -> str | None   repo identifier (matches ~/.claude/projects/<slug>/)
  resolve_abs_path(path)       -> str          absolute, symlink-resolved path
  file_mtime(path)             -> int | None   epoch-seconds mtime, or None if missing
  tools_dir()                  -> str | None   absolute path to tools/
  project_config_path()        -> str | None   absolute path to project-config.md
  die(message, code=2)         -> NoReturn     print "STOP: ..." to stderr and exit
  warn(message)                -> None         print "WARN: ..." to stderr
  banner(name=None)            -> None         print the tool's identity line to stderr
  require_cmd(*cmds)           -> None         die() if any command is missing
  run_gate(label, cmd)         -> int          run a build command with summarised output

@author Samson Paul, samson.paul@experionglobal.com
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time


def die(message, code=2):
    """Print to stderr and exit. Default exit code 2, per the tool contract."""
    print(f"STOP: {message}", file=sys.stderr)
    sys.exit(code)


def warn(message):
    """Print to stderr without exiting."""
    print(f"WARN: {message}", file=sys.stderr)


def banner(name=None):
    """Print the tool's identity line.

    Goes to stderr on purpose: a caller may parse a tool's stdout directly
    (e.g. to capture a single emitted path or value), so stdout must stay
    machine-clean of anything but the tool's actual output.

    Falls back to the containing directory name, which is the tool's identity
    under the tools/<name>/<name>.py convention.
    """
    resolved = name or os.path.basename(os.path.dirname(resolve_abs_path(sys.argv[0])))
    print(f"[custom tool] {resolved}", file=sys.stderr)


def require_cmd(*cmds):
    """Verify required commands exist on PATH. die() if any are missing."""
    missing = [cmd for cmd in cmds if shutil.which(cmd) is None]
    if missing:
        die("missing required command(s): " + " ".join(missing))


def resolve_abs_path(path):
    """Absolute, symlink-resolved path (equivalent to GNU `readlink -f`)."""
    return os.path.realpath(path)


def file_mtime(path):
    """Epoch-seconds mtime of a file, or None if it does not exist."""
    if not os.path.isfile(path):
        return None
    return int(os.path.getmtime(path))


def _run_git(args):
    """Run a git command, returning trimmed stdout or None on failure."""
    try:
        result = subprocess.run(["git", *args], stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, text=True)
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def repo_root():
    """Absolute path to the git repo root, honouring CLAUDE_PROJECT_DIR. None if not a repo."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir and os.path.isdir(os.path.join(project_dir, ".git")):
        return project_dir
    return _run_git(["rev-parse", "--show-toplevel"]) or None


def _slugify(text):
    return re.sub(r"[^a-zA-Z0-9-]", "-", text)


def project_slug():
    """Cross-worktree-stable project identifier for ~/.claude/projects/<slug>/."""
    url = _run_git(["config", "--get", "remote.origin.url"])
    if url:
        return _slugify(url)
    common_dir = _run_git(["rev-parse", "--git-common-dir"])
    if common_dir:
        if not os.path.isabs(common_dir):
            common_dir = os.path.join(os.getcwd(), common_dir)
        return _slugify(os.path.dirname(common_dir))
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        return _slugify(project_dir)
    root = repo_root()
    return _slugify(root) if root else None


def tools_dir():
    """Absolute path to tools/, or None if not in a repo."""
    root = repo_root()
    return os.path.join(root, "tools") if root else None


def project_config_path():
    """Absolute path to project-config.md, or None if not in a repo."""
    root = repo_root()
    return os.path.join(root, ".claude", "shared", "project-config.md") if root else None


_GATE_ERROR_MARKERS = re.compile(
    r"error:|^e: |FAILURE:|FAILED|^> Task .* FAILED|What went wrong:")


def _sanitize_label(label):
    """Replace anything outside [A-Za-z0-9._-] with '-'; die() on empty/./.. ."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", label)
    if safe in ("", ".", ".."):
        die(f"run_gate: invalid label '{label}'")
    return safe


def run_gate(label, cmd):
    """Run a build command, capturing output to a log and emitting a short summary.

    On success prints one PASS line and removes the log. On failure prints a FAIL
    line, up to 40 error-marker excerpts (with line numbers), and the log path.
    Returns the underlying command's exit code. `cmd` is run as-is via the shell.
    """
    label = _sanitize_label(label)
    tmp_dir = tempfile.gettempdir()
    log = os.path.join(tmp_dir, f"{label}-latest.log")

    try:
        log_handle = open(log, "w")
    except OSError:
        die(f"run_gate: cannot write log file: {log}")

    start = time.time()
    with log_handle:
        status = subprocess.run(cmd, shell=True, stdout=log_handle,
                                stderr=subprocess.STDOUT).returncode
    elapsed = int(time.time() - start)

    if status == 0:
        print(f"PASS {label} ({elapsed}s)")
        try:
            os.remove(log)
        except OSError:
            pass
        return 0

    print(f"FAIL {label} ({elapsed}s, exit {status})\n\n--- error excerpts ---")
    _print_gate_excerpts(log)
    print(f"\nFull log: {log}")
    return status


def _print_gate_excerpts(log):
    """Print up to 40 error-marker lines (numbered) from a gate log."""
    try:
        with open(log, encoding="utf-8", errors="replace") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return
    shown = 0
    for number, line in enumerate(lines, start=1):
        if _GATE_ERROR_MARKERS.search(line):
            print(f"{number}:{line}")
            shown += 1
            if shown >= 40:
                break
