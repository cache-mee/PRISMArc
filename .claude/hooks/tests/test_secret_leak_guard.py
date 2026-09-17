"""Tests for .claude/hooks/secret-leak-guard.py.

Covers the fail-closed behavior added for this hook specifically (malformed
stdin JSON, unexpected internal exceptions) as well as the pre-existing
leak-detection and no-op behavior, to guard against regressions.

@author Samson Paul, samson.paul@experionglobal.com
"""
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

HOOK_PATH = Path(__file__).resolve().parent.parent / "secret-leak-guard.py"


def _load_module():
    """Import secret-leak-guard.py as a fresh module (filename has a hyphen,
    so it can't be imported via a normal `import` statement)."""
    spec = importlib.util.spec_from_file_location("secret_leak_guard", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def guard(monkeypatch):
    """A freshly-imported module instance per test, so monkeypatches on it
    (e.g. os.environ, internal functions) never leak across tests."""
    return _load_module()


def _run_main(guard_module, monkeypatch, stdin_text):
    """Run guard_module.main() with the given stdin text, capturing stdout.
    Returns the parsed JSON decision."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    captured = io.StringIO()
    monkeypatch.setattr(sys, "stdout", captured)
    guard_module.main()
    return json.loads(captured.getvalue())


def test_blocks_command_embedding_sensitive_env_value(guard, monkeypatch):
    monkeypatch.setenv("MY_SECRET_TOKEN", "abcdefghijklmnop")  # len >= 12
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "curl -H 'Authorization: Bearer abcdefghijklmnop'"},
    })

    result = _run_main(guard, monkeypatch, payload)

    assert result.get("decision") == "block"
    assert "MY_SECRET_TOKEN" in result["reason"]
    assert "abcdefghijklmnop" not in result["reason"]


def test_allows_safe_command_with_no_sensitive_values(guard, monkeypatch):
    monkeypatch.setenv("MY_SECRET_TOKEN", "abcdefghijklmnop")
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la /tmp"},
    })

    result = _run_main(guard, monkeypatch, payload)

    assert result == {}


def test_malformed_json_stdin_now_blocks(guard, monkeypatch):
    result = _run_main(guard, monkeypatch, "{not valid json")

    assert result.get("decision") == "block"
    assert "fail" in result["reason"].lower()


def test_non_bash_tool_is_still_a_noop(guard, monkeypatch):
    payload = json.dumps({
        "tool_name": "Read",
        "tool_input": {"file_path": "/etc/hosts"},
    })

    result = _run_main(guard, monkeypatch, payload)

    assert result == {}


def test_empty_command_is_still_a_noop(guard, monkeypatch):
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": ""},
    })

    result = _run_main(guard, monkeypatch, payload)

    assert result == {}


def test_unexpected_internal_exception_still_yields_valid_block_json(guard, monkeypatch):
    def _boom(command):
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr(guard, "_find_leak", _boom)

    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "echo hello"},
    })

    result = _run_main(guard, monkeypatch, payload)

    assert result.get("decision") == "block"
    assert "RuntimeError" in result["reason"]
