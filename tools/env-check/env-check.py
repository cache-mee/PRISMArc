#!/usr/bin/env python3
"""Report whether environment variables are set — never prints their values.

Usage:
  env-check.py <VAR> [<VAR> ...]    Print "<NAME>: SET|EMPTY|UNSET" per var
  env-check.py --help

Exists because hand-writing a shell one-liner to test a credential's presence
can leak it into a transcript: `${VAR:-UNSET}` expands to the variable's VALUE
when VAR is set, because `:-` is the default-value operator. This tool cannot
emit a value at all — it only ever prints one of three state labels. Used by
`.claude/hooks/secret-leak-guard.py`'s block message as the safe alternative
to embedding a credential's value in a Bash command.

@author Samson Paul, samson.paul@experionglobal.com
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
from common import banner, die  # noqa: E402

USAGE = """env-check — report whether env vars are set, without printing their values

USAGE:
    env-check <VAR> [<VAR> ...]   Print "<NAME>: SET|EMPTY|UNSET" per var
    env-check --help              This help

OUTPUT:
    One line per variable, in the order given:
        <NAME>: SET      present and non-empty
        <NAME>: EMPTY    present but empty string
        <NAME>: UNSET    not present in the environment

    The value is never printed, so this is safe for credentials.

EXIT:
    0  every named variable is SET
    1  at least one is EMPTY or UNSET
    2  error (no variable names given)

EXAMPLES:
    env-check JIRA_API_TOKEN CONFLUENCE_API_TOKEN
    # → JIRA_API_TOKEN: SET
    #   CONFLUENCE_API_TOKEN: UNSET
    # exit 1

    env-check JIRA_API_TOKEN && echo "ready"
    # → JIRA_API_TOKEN: SET
    #   ready"""

STATE_SET = "SET"
STATE_EMPTY = "EMPTY"
STATE_UNSET = "UNSET"


def state_for(variable_name):
    """Return the state label for one variable. Never returns the value."""
    if variable_name not in os.environ:
        return STATE_UNSET
    if os.environ[variable_name] == "":
        return STATE_EMPTY
    return STATE_SET


def main():
    banner()
    variable_names = sys.argv[1:]

    if not variable_names:
        print(USAGE)
        die("no variable names given")

    if variable_names[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    every_variable_is_set = True
    for variable_name in variable_names:
        state = state_for(variable_name)
        print(f"{variable_name}: {state}")
        if state != STATE_SET:
            every_variable_is_set = False

    sys.exit(0 if every_variable_is_set else 1)


if __name__ == "__main__":
    main()
