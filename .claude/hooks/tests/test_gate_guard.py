"""Tests for `.claude/hooks/gate-guard.py`.

Invokes the hook script as a subprocess (matching how Claude Code actually
runs it: JSON on stdin, JSON on stdout) rather than importing it, so the test
also exercises the real stdin/stdout contract.

@author Samson Paul, samson.paul@experionglobal.com
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).resolve().parent.parent / "gate-guard.py"


def run_hook(command, tool_name="Bash", raw_stdin=None):
    """Run the hook with the given Bash command (or raw stdin string) and
    return the parsed JSON response."""
    if raw_stdin is None:
        payload = json.dumps({"tool_name": tool_name, "tool_input": {"command": command}})
    else:
        payload = raw_stdin

    result = subprocess.run(
        [sys.executable, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"hook exited nonzero: {result.stderr}"
    return json.loads(result.stdout)


BLOCKED_COMMANDS = [
    ("git merge", "git merge feature/foo"),
    ("gh pr merge (no flags)", "gh pr merge"),
    ("gh pr merge (with flags)", "gh pr merge 123 --squash"),
    ("git reset --hard", "git reset --hard origin/main"),
    ("git clean -fd", "git clean -fd"),
    ("git clean -fdx", "git clean -fdx"),
    ("git clean -f -d", "git clean -f -d"),
    ("git branch -D", "git branch -D old-feature"),
    ("rm -rf", "rm -rf ./build"),
    ("rm -fr", "rm -fr ./build"),
    ("rm --recursive --force", "rm --recursive --force B2B_BE/app"),
    ("git push to main", "git push origin main"),
    ("git push HEAD:main", "git push origin HEAD:main"),
    ("git push to master", "git push origin master"),
    ("git push to develop", "git push origin develop"),
    ("git push --force", "git push --force origin feature/foo"),
    ("git push --force-with-lease", "git push --force-with-lease origin feature/foo"),
    ("git push -f", "git push -f origin feature/foo"),
    ("tag then push", "git tag v1.0 && git push origin v1.0"),
    ("npm install <pkg>", "npm install left-pad"),
    ("npm add <pkg>", "npm add left-pad"),
    ("pip install <pkg>", "pip install requests"),
    ("poetry add <pkg>", "poetry add requests"),
    ("uv add <pkg>", "uv add requests"),
]


@pytest.mark.parametrize("label,command", BLOCKED_COMMANDS)
def test_blocks_gate_triggers(label, command):
    result = run_hook(command)
    assert result.get("decision") == "block", f"{label}: expected block, got {result}"
    assert command.split(" ")[0] in result.get("reason", "") or "command" in result.get("reason", "").lower()


SAFE_COMMANDS = [
    "git status",
    "git push origin feature/foo",
    'git commit -m "some message"',
    "ls -la",
    "npm test",
    "git log --oneline -10",
    "git branch -d already-merged-branch",
    "npm install",
    "pip install -r requirements.txt",
    "rm -rf node_modules",
    "rm -rf dist/",
    "rm -rf build/",
    "rm -rf /tmp/scratch-dir",
    "rm -rf .pytest_cache __pycache__",
]


@pytest.mark.parametrize("command", SAFE_COMMANDS)
def test_allows_safe_commands(command):
    result = run_hook(command)
    assert result == {}, f"expected no decision for {command!r}, got {result}"


def test_non_bash_tool_is_ignored():
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
    result = run_hook(None, raw_stdin=payload)
    assert result == {}


def test_malformed_json_fails_closed():
    result = run_hook(None, raw_stdin="{not valid json")
    assert result.get("decision") == "block"
    assert "reason" in result


def test_empty_command_is_ignored():
    result = run_hook("")
    assert result == {}


def test_merge_message_names_gate_and_shows_command():
    result = run_hook("git merge feature/x")
    reason = result["reason"]
    assert "merge" in reason
    assert "gates.json" in reason
    assert "human" in reason.lower()
    assert "git merge feature/x" in reason


def test_destructive_message_shows_full_command_not_redacted():
    result = run_hook("rm -rf /home/user/important-data")
    reason = result["reason"]
    assert "rm -rf /home/user/important-data" in reason


def test_safe_rm_paths_are_not_redacted_as_a_side_effect():
    """Regression check: rm -rf confined to a disposable path must be allowed
    outright, not merely have its message redacted."""
    for safe_command in ("rm -rf node_modules", "rm -rf /tmp/scratch-dir"):
        result = run_hook(safe_command)
        assert result == {}, f"expected no decision for {safe_command!r}, got {result}"
