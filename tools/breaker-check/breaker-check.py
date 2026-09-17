#!/usr/bin/env python3
"""Evaluate .orchestration/policy/{breakers,retry-limits}.json against a run's status.json.

Makes the breaker policy real: `breakers.json` and `retry-limits.json` today
state their own triggers as `convention_only` / "not enforced by any
runtime". This tool is that runtime check — a deterministic pass/fail over a
run's durable state, never over an agent's own claim that it is fine.

Usage:
  breaker-check.py --run-dir <path> [--repo-root <path>] [--ticket <id>]
  breaker-check.py record-attempt --run-dir <path> --activity <key>
                                   --reason <r> --failure-signal <s>
                                   --evidence <path>
                                   [--current-agent <a>] [--current-state <s>]
                                   [--next-action <s>] [--status <s>]
  breaker-check.py --help

EXIT:
  0  PASS — no breaker tripped (includes: no status.json yet, nothing to
     evaluate); or record-attempt succeeded
  1  FAIL — one or more breakers tripped
  2  usage/error (malformed status.json, or missing/malformed
     retry-limits.json / breakers.json under --repo-root)

@author Samson Paul, samson.paul@experionglobal.com
"""
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_lib"))
from common import banner, die, repo_root as _git_repo_root  # noqa: E402

USAGE = """breaker-check — evaluate policy/*.json breakers against a run's status.json

USAGE:
    breaker-check --run-dir <path> [--repo-root <path>] [--ticket <id>]
    breaker-check record-attempt --run-dir <path> --activity <key>
                                  --reason <r> --failure-signal <s>
                                  --evidence <path>
                                  [--current-agent <a>] [--current-state <s>]
                                  [--next-action <s>] [--status <s>]
    breaker-check --help

ARGS:
    --run-dir <path>    .orchestration/runs/<WORK-ID>/ to evaluate (required)
    --repo-root <path>  repo root (default: `git rev-parse --show-toplevel`
                         from cwd)
    --ticket <id>       ticket/work-id string; enables the budget-exceeded
                         check only

record-attempt writes the one piece of durable state a breaker check needs
and that nothing else in this repo writes deterministically: it appends a
well-formed entry to {run-dir}/status.json's attempts[], creating a minimal
valid status.json (per .orchestration/schemas/status.json) if none exists
yet. Call this instead of hand-editing status.json — malformed JSON there
would make every later breaker-check call fail with exit 2.

EXIT:
    0  PASS — no breaker tripped (includes: no status.json yet); or
       record-attempt succeeded
    1  FAIL — one or more breakers tripped
    2  usage/error
"""

BUDGET_SUBPROCESS_TIMEOUT_S = 10


# ---------------------------------------------------------------------------
# arg parsing
# ---------------------------------------------------------------------------

def parse_args(argv):
    if not argv:
        print(USAGE)
        die("--run-dir is required", 2)
    if argv[0] in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    run_dir = None
    repo_root_arg = None
    ticket = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--run-dir":
            if i + 1 >= len(argv):
                die("--run-dir requires a value", 2)
            run_dir = argv[i + 1]; i += 2
        elif arg == "--repo-root":
            if i + 1 >= len(argv):
                die("--repo-root requires a value", 2)
            repo_root_arg = argv[i + 1]; i += 2
        elif arg == "--ticket":
            if i + 1 >= len(argv):
                die("--ticket requires a value", 2)
            ticket = argv[i + 1]; i += 2
        else:
            die(f"unknown argument: {arg} (try --help)", 2)

    if not run_dir:
        die("--run-dir is required", 2)
    return run_dir, repo_root_arg, ticket


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def resolve_repo_root(repo_root_arg):
    if repo_root_arg:
        if not os.path.isdir(repo_root_arg):
            die(f"--repo-root does not exist or is not a directory: {repo_root_arg}", 2)
        return os.path.abspath(repo_root_arg)
    root = _git_repo_root()
    if not root:
        die("could not resolve repo root via `git rev-parse --show-toplevel` "
            "— pass --repo-root explicitly", 2)
    return root


def load_json_required(path, what):
    """Load a JSON file that MUST exist and MUST parse. die(2) otherwise."""
    if not os.path.isfile(path):
        die(f"{what} not found at {path} (required)", 2)
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        die(f"{what} at {path} is not valid JSON: {exc}", 2)


def load_json_optional(path):
    """Load a JSON file that may legitimately be absent. Returns None if so."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        die(f"{path} exists but is not valid JSON: {exc}", 2)


def find_key_anywhere(obj, key):
    """First value found for `key` anywhere in a nested dict/list structure."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = find_key_anywhere(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_key_anywhere(item, key)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------
# individual breaker checks — each returns (evaluated: bool, tripped: bool, line: str|None)
# ---------------------------------------------------------------------------

def check_attempt_limit(status, retry_limits, breakers_map):
    attempts = status.get("attempts") or []
    groups = {}
    for entry in attempts:
        groups.setdefault(entry.get("activity"), []).append(entry)

    limits = retry_limits.get("limits", {}) or {}
    defaults = retry_limits.get("defaults", {}) or {}
    fallback_action = breakers_map.get("attempt-limit", "stop_and_escalate")

    lines = []
    tripped = False
    for activity, group in groups.items():
        entry = limits.get(activity)
        if entry is not None:
            max_attempts = entry.get("max_attempts", defaults.get("max_attempts"))
            action = entry.get("on_exhaustion") or defaults.get("on_exhaustion") or fallback_action
        else:
            max_attempts = defaults.get("max_attempts")
            action = defaults.get("on_exhaustion") or fallback_action
        count = len(group)
        if max_attempts is not None and count >= max_attempts:
            tripped = True
            lines.append(
                f"attempt-limit: TRIPPED — activity '{activity}' at {count}/{max_attempts} "
                f"attempts -> {action}")

    if not lines:
        lines.append("attempt-limit: ok")
    return True, tripped, lines


def check_no_progress(status, breakers_map):
    attempts = status.get("attempts") or []
    groups = {}
    for entry in attempts:
        groups.setdefault(entry.get("activity"), []).append(entry)
    action = breakers_map.get("no-progress", "stop_and_escalate")

    lines = []
    tripped = False
    for activity, group in groups.items():
        ordered = sorted(group, key=lambda e: e.get("n", 0))
        if len(ordered) < 2:
            continue
        last_two = ordered[-2:]
        sig_a = last_two[0].get("failure_signal")
        sig_b = last_two[1].get("failure_signal")
        if sig_a is not None and sig_a == sig_b:
            tripped = True
            lines.append(
                f"no-progress: TRIPPED — activity '{activity}' repeated failure_signal "
                f"'{sig_b}' across attempts {last_two[0].get('n')} and {last_two[1].get('n')} "
                f"-> {action}")

    if not lines:
        lines.append("no-progress: ok")
    return True, tripped, lines


def check_evidence_conflict(status, run_dir, repo_root, breakers_map):
    evidence_index = status.get("evidence_index") or []
    action = breakers_map.get("evidence-conflict", "stop_and_escalate")

    lines = []
    tripped = False
    for path in evidence_index:
        candidate_run = os.path.join(run_dir, path)
        candidate_repo = os.path.join(repo_root, path)
        if os.path.isfile(candidate_run) or os.path.isfile(candidate_repo):
            continue
        tripped = True
        lines.append(
            f"evidence-conflict: TRIPPED — evidence path not found: '{path}' "
            f"(checked {candidate_run} and {candidate_repo}) -> {action}")

    if not lines:
        lines.append("evidence-conflict: ok")
    return True, tripped, lines


def check_gate_encountered(status, breakers_map):
    gate = status.get("gate")
    action = breakers_map.get("gate-encountered", "stop_and_await_human")
    if gate:
        gate_id = gate.get("id", "?")
        question = gate.get("question", "?")
        line = (f"gate-encountered: TRIPPED — work correctly stopped at gate "
                f"'{gate_id}': {question} -> {action}")
        return True, True, [line]
    return True, False, ["gate-encountered: ok"]


REQUIRED_HANDOFF_SECTIONS = [
    "Work ID", "Objective", "Acceptance Criteria", "Current State", "Completed",
    "Constraints", "Decisions", "Evidence", "Next Action", "Completion Condition",
    "Escalation",
]


def check_handoff_insufficient(run_dir, breakers_map):
    handoff_path = os.path.join(run_dir, "handoff.md")
    if not os.path.isfile(handoff_path):
        return False, False, []  # not applicable — no line printed

    try:
        with open(handoff_path, encoding="utf-8") as handle:
            content = handle.read()
    except OSError as exc:
        die(f"could not read {handoff_path}: {exc}", 2)

    lowered = content.lower()
    missing = [section for section in REQUIRED_HANDOFF_SECTIONS
               if section.lower() not in lowered]
    if "failed" not in lowered or "unresolved" not in lowered:
        missing.append("Failed / Unresolved")

    action = breakers_map.get("handoff-insufficient", "stop_and_request_repair")
    if missing:
        line = (f"handoff-insufficient: TRIPPED — missing section(s): "
                f"{', '.join(missing)} -> {action}")
        return True, True, [line]
    return True, False, ["handoff-insufficient: ok"]


def check_budget_exceeded(budget_limits, repo_root, ticket):
    if budget_limits is None or not ticket:
        return False, False, []  # not applicable — no line printed

    metrics_py = os.path.join(repo_root, "tools", "agent-metrics", "metrics.py")
    try:
        result = subprocess.run(
            [sys.executable, metrics_py, "report", "--where", f"ticket={ticket}", "--json"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            timeout=BUDGET_SUBPROCESS_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return True, False, [f"budget-exceeded: SKIP (agent-metrics unavailable: "
                              f"timed out after {BUDGET_SUBPROCESS_TIMEOUT_S}s)"]
    except OSError as exc:
        return True, False, [f"budget-exceeded: SKIP (agent-metrics unavailable: {exc})"]

    if result.returncode != 0:
        return True, False, [f"budget-exceeded: SKIP (agent-metrics unavailable: "
                              f"metrics.py exited {result.returncode})"]

    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return True, False, ["budget-exceeded: SKIP (agent-metrics unavailable: "
                              "unparseable JSON output)"]

    if isinstance(rows, dict):
        rows = rows.get("rows", [])
    if not isinstance(rows, list):
        return True, False, ["budget-exceeded: SKIP (agent-metrics unavailable: "
                              "unexpected report output shape)"]

    total_cost = sum(r.get("cost_usd") or 0 for r in rows if isinstance(r, dict))

    ceiling = None
    defaults = budget_limits.get("defaults") if isinstance(budget_limits, dict) else None
    if isinstance(defaults, dict):
        ceiling = defaults.get("ceiling_usd")
    if ceiling is None:
        ceiling = find_key_anywhere(budget_limits, "ceiling_usd")
    if ceiling is None:
        return True, False, ["budget-exceeded: SKIP (no ceiling_usd found in "
                              "budget-limits.json)"]

    action = None
    if isinstance(defaults, dict):
        action = defaults.get("on_ceiling_exceeded")
    if action is None:
        action = find_key_anywhere(budget_limits, "on_ceiling_exceeded")
    action = action or "stop_and_escalate"

    if total_cost > ceiling:
        return True, True, [f"budget-exceeded: TRIPPED — ticket '{ticket}' cost "
                             f"${total_cost:.2f} exceeds ceiling ${ceiling:.2f} -> {action}"]
    return True, False, [f"budget-exceeded: ok (${total_cost:.2f} / ${ceiling:.2f})"]


# ---------------------------------------------------------------------------
# record-attempt: the deterministic writer for status.json's attempts[].
# Agents/skills call this instead of hand-editing the file — a malformed
# hand-edit would make every later breaker-check call fail with exit 2.
# ---------------------------------------------------------------------------

REQUIRED_STATUS_FIELDS = [
    "work_id", "status", "current_agent", "current_state", "attempts",
    "next_action", "updated_at",
]


def parse_record_attempt_args(argv):
    required = {"--run-dir": None, "--activity": None, "--reason": None,
                "--failure-signal": None, "--evidence": None}
    optional = {"--current-agent": None, "--current-state": None,
                "--next-action": None, "--status": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in required or arg in optional:
            if i + 1 >= len(argv):
                die(f"{arg} requires a value", 2)
            (required if arg in required else optional)[arg] = argv[i + 1]
            i += 2
        else:
            die(f"unknown argument: {arg} (try --help)", 2)
    missing = [k for k, v in required.items() if v is None]
    if missing:
        die(f"record-attempt missing required argument(s): {', '.join(missing)}", 2)
    return required, optional


def cmd_record_attempt(argv):
    banner()
    required, optional = parse_record_attempt_args(argv)
    run_dir = os.path.abspath(required["--run-dir"])
    os.makedirs(run_dir, exist_ok=True)
    status_path = os.path.join(run_dir, "status.json")

    status = load_json_optional(status_path)
    if status is None:
        status = {
            "work_id": os.path.basename(run_dir.rstrip(os.sep)),
            "status": optional["--status"] or "in_progress",
            "current_agent": optional["--current-agent"],
            "current_state": optional["--current-state"] or (
                f"Recovery attempt in progress for '{required['--activity']}'."),
            "attempts": [],
            "next_action": optional["--next-action"] or (
                f"Retry '{required['--activity']}' if permitted; otherwise stop and escalate."),
            "gate": None,
            "breaker_tripped": None,
            "escalation": None,
            "evidence_index": [],
        }
    else:
        for key in REQUIRED_STATUS_FIELDS:
            if key not in status:
                die(f"{status_path} is missing required field '{key}' — cannot append safely; "
                    f"fix or remove the file", 2)
        if optional["--status"]:
            status["status"] = optional["--status"]
        if optional["--current-agent"]:
            status["current_agent"] = optional["--current-agent"]
        if optional["--current-state"]:
            status["current_state"] = optional["--current-state"]
        if optional["--next-action"]:
            status["next_action"] = optional["--next-action"]

    activity = required["--activity"]
    existing_n = [a.get("n", 0) for a in status["attempts"] if a.get("activity") == activity]
    entry = {
        "n": (max(existing_n) + 1) if existing_n else 1,
        "activity": activity,
        "reason": required["--reason"],
        "failure_signal": required["--failure-signal"],
        "evidence": required["--evidence"],
    }
    status["attempts"].append(entry)

    evidence_index = status.get("evidence_index") or []
    if entry["evidence"] not in evidence_index:
        evidence_index.append(entry["evidence"])
    status["evidence_index"] = evidence_index

    status["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(status_path, "w", encoding="utf-8") as handle:
        json.dump(status, handle, indent=2)
        handle.write("\n")

    print(f"OK recorded attempt n={entry['n']} for '{activity}' in {status_path}")
    sys.exit(0)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "record-attempt":
        cmd_record_attempt(sys.argv[2:])
        return

    banner()
    run_dir_arg, repo_root_arg, ticket = parse_args(sys.argv[1:])

    run_dir = os.path.abspath(run_dir_arg)
    repo_root = resolve_repo_root(repo_root_arg)

    status_path = os.path.join(run_dir, "status.json")
    if not os.path.isfile(status_path):
        print(f"SKIP breaker-check (no status.json at {status_path} — nothing to evaluate)")
        sys.exit(0)

    try:
        with open(status_path, encoding="utf-8") as handle:
            status = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        die(f"status.json at {status_path} is not valid JSON: {exc}", 2)

    retry_limits = load_json_required(
        os.path.join(repo_root, ".orchestration", "policy", "retry-limits.json"),
        "retry-limits.json")
    breakers_policy = load_json_required(
        os.path.join(repo_root, ".orchestration", "policy", "breakers.json"),
        "breakers.json")
    breakers_map = {b.get("id"): b.get("action") for b in breakers_policy.get("breakers", [])}

    budget_limits = load_json_optional(
        os.path.join(repo_root, ".orchestration", "policy", "budget-limits.json"))

    any_tripped = False
    all_lines = []

    for evaluated, tripped, lines in (
        check_attempt_limit(status, retry_limits, breakers_map),
        check_no_progress(status, breakers_map),
        check_evidence_conflict(status, run_dir, repo_root, breakers_map),
        check_gate_encountered(status, breakers_map),
        check_handoff_insufficient(run_dir, breakers_map),
        check_budget_exceeded(budget_limits, repo_root, ticket),
    ):
        if not evaluated:
            continue
        all_lines.extend(lines)
        any_tripped = any_tripped or tripped

    for line in all_lines:
        print(line)

    tripped_count = sum(1 for line in all_lines if "TRIPPED" in line)
    if any_tripped:
        print(f"FAIL breaker-check ({tripped_count} breaker(s) tripped)")
        sys.exit(1)

    print("PASS breaker-check")
    sys.exit(0)


if __name__ == "__main__":
    main()
