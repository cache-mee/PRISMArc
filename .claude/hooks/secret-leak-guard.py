#!/usr/bin/env python3
"""PreToolUse hook: Block Bash commands that embed the VALUE of a sensitive env var.

Claude Code displays `tool_input.command` literally — if the model embeds a secret's
actual value (API key, token, password) rather than referencing it via $VAR, that
value appears on screen, in the transcript, and in shell history.

This hook scans the command string for the values of env vars whose NAMES match common
secret-naming patterns and blocks the call with an instructive message, telling the
model to use $VAR_NAME syntax instead so the shell expands it at runtime.

Patterns of env var names that are treated as sensitive:
  *PAT*, *TOKEN*, *KEY*, *SECRET*, *PASSWORD*, *PASSWD*, *PRIVATE*
(Minimum value length of 12 chars to avoid false positives on short innocent vars.)

The error message itself redacts matched values as `****` so it doesn't leak them either.

No hardcoded project-specific values in this script.

@author Samson Paul, samson.paul@experionglobal.com
"""
import fnmatch
import json
import os
import sys


SENSITIVE_NAME_PATTERNS = [
    "*PAT*", "*TOKEN*", "*KEY*", "*SECRET*",
    "*PASSWORD*", "*PASSWD*", "*PRIVATE*",
]

# Don't treat these as secrets even if their name matches — they're known benign
BENIGN_NAMES = {
    "PATH", "SHELLPATH", "MANPATH", "INFOPATH", "CLASSPATH", "LD_LIBRARY_PATH",
    "XDG_DATA_DIRS", "XDG_CONFIG_DIRS", "JAVA_HOME",
}

MIN_SECRET_LEN = 12


def _sensitive_env_values():
    """Yield (var_name, var_value) for env vars likely to hold secrets."""
    for name, value in os.environ.items():
        if name in BENIGN_NAMES:
            continue
        if not value or len(value) < MIN_SECRET_LEN:
            continue
        if any(fnmatch.fnmatchcase(name, pat) for pat in SENSITIVE_NAME_PATTERNS):
            yield name, value


def _find_leak(command):
    """Return (var_name, value) of the first sensitive env var whose value appears
    verbatim in the command string, or None if no leak detected."""
    for name, value in _sensitive_env_values():
        if value in command:
            return name, value
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        json.dump({}, sys.stdout)
        return

    if data.get("tool_name") != "Bash":
        json.dump({}, sys.stdout)
        return

    command = (data.get("tool_input", {}).get("command") or "")
    if not command:
        json.dump({}, sys.stdout)
        return

    leak = _find_leak(command)
    if not leak:
        json.dump({}, sys.stdout)
        return

    var_name, value = leak
    # Redact the value in the message so the block reason doesn't re-leak it.
    redacted = command.replace(value, "****")
    if len(redacted) > 300:
        redacted = redacted[:300] + "...(truncated)"

    json.dump({
        "decision": "block",
        "reason": (
            f"BLOCKED: Command embeds the raw value of a sensitive env var (`{var_name}`). "
            f"The value would appear on screen, in the transcript, and in shell history.\n\n"
            f"Use shell variable syntax so the shell expands it at runtime — the display "
            f"will show only the variable name:\n\n"
            f"  BAD:  curl -H \"Authorization: Bearer <raw-value>\" ...\n"
            f"  GOOD: curl -H \"Authorization: Bearer ${{{var_name}}}\" ...\n\n"
            f"To check whether a credential is set without risking this, use "
            f"`tools/env-check/env-check {var_name}` — it reports SET/EMPTY/UNSET and "
            f"never prints the value.\n\n"
            f"Your command (redacted): {redacted}"
        ),
    }, sys.stdout)


if __name__ == "__main__":
    main()
