"""Tests for breaker-check.py — run as subprocess against the built CLI.

Run: python3 -m pytest tools/breaker-check/tests/ -v

@author Samson Paul, samson.paul@experionglobal.com
"""
import json
import os
import subprocess
import sys

import pytest

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "breaker-check.py")

RETRY_LIMITS = {
    "version": 1,
    "defaults": {"max_attempts": 3, "on_exhaustion": "stop_and_escalate"},
    "limits": {
        "implementation_fix": {"max_attempts": 3, "on_exhaustion": "stop_and_escalate"},
        "test_repair": {"max_attempts": 2, "on_exhaustion": "stop_and_escalate"},
    },
}

BREAKERS = {
    "version": 1,
    "breakers": [
        {"id": "attempt-limit", "action": "stop_and_escalate"},
        {"id": "no-progress", "action": "stop_and_escalate"},
        {"id": "evidence-conflict", "action": "stop_and_escalate"},
        {"id": "gate-encountered", "action": "stop_and_await_human"},
        {"id": "handoff-insufficient", "action": "stop_and_request_repair"},
    ],
}


def run_cli(args):
    result = subprocess.run([sys.executable, SCRIPT, *args],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result.returncode, result.stdout, result.stderr


def make_repo_root(tmp_path, with_retry_limits=True, with_breakers=True,
                    budget_limits=None):
    repo_root = tmp_path / "repo"
    policy_dir = repo_root / ".orchestration" / "policy"
    policy_dir.mkdir(parents=True)
    if with_retry_limits:
        (policy_dir / "retry-limits.json").write_text(json.dumps(RETRY_LIMITS))
    if with_breakers:
        (policy_dir / "breakers.json").write_text(json.dumps(BREAKERS))
    if budget_limits is not None:
        (policy_dir / "budget-limits.json").write_text(json.dumps(budget_limits))
    return repo_root


def make_run_dir(tmp_path, name="run"):
    run_dir = tmp_path / name
    run_dir.mkdir()
    return run_dir


def write_status(run_dir, status_obj):
    (run_dir / "status.json").write_text(json.dumps(status_obj))


BASE_STATUS = {
    "work_id": "SALON-1",
    "status": "in_progress",
    "current_agent": "developer",
    "current_state": "working",
    "attempts": [],
    "next_action": "do the thing",
    "updated_at": "2026-01-01T00:00:00Z",
}


VALID_HANDOFF = """# Handoff

## Work ID
SALON-1

## Objective
Do the thing.

## Acceptance Criteria
1. It works.

## Current State
In progress.

## Completed
- Nothing yet.

## Failed / Unresolved
- Nothing failed yet, nothing unresolved.

## Constraints
None.

## Decisions
None yet.

## Evidence
None yet.

## Next Action
Do the thing.

## Completion Condition
Tests pass.

## Escalation
None.
"""


# ---------------------------------------------------------------------------

def test_no_status_json_exits_zero_with_skip(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 0
    assert "SKIP breaker-check" in out
    assert "no status.json" in out


def test_malformed_status_json_exits_two(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    (run_dir / "status.json").write_text("{not valid json")
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 2


def test_missing_retry_limits_exits_two(tmp_path):
    repo_root = make_repo_root(tmp_path, with_retry_limits=False)
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 2


def test_missing_breakers_json_exits_two(tmp_path):
    repo_root = make_repo_root(tmp_path, with_breakers=False)
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 2


def test_attempt_limit_trips_at_max(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    status = dict(BASE_STATUS)
    status["attempts"] = [
        {"n": 1, "activity": "test_repair", "reason": "r1", "failure_signal": "sig-a",
         "evidence": "e1.md"},
        {"n": 2, "activity": "test_repair", "reason": "r2", "failure_signal": "sig-b",
         "evidence": "e2.md"},
    ]
    write_status(run_dir, status)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 1
    assert "attempt-limit: TRIPPED" in out
    assert "test_repair" in out


def test_no_progress_trips_on_repeated_failure_signal(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    status = dict(BASE_STATUS)
    status["attempts"] = [
        {"n": 1, "activity": "implementation_fix", "reason": "r1",
         "failure_signal": "same-signal", "evidence": "e1.md"},
        {"n": 2, "activity": "implementation_fix", "reason": "r2",
         "failure_signal": "same-signal", "evidence": "e2.md"},
    ]
    write_status(run_dir, status)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 1
    assert "no-progress: TRIPPED" in out


def test_no_progress_does_not_trip_when_signal_changed(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    status = dict(BASE_STATUS)
    status["attempts"] = [
        {"n": 1, "activity": "implementation_fix", "reason": "r1",
         "failure_signal": "signal-one", "evidence": "e1.md"},
        {"n": 2, "activity": "implementation_fix", "reason": "r2",
         "failure_signal": "signal-two", "evidence": "e2.md"},
    ]
    write_status(run_dir, status)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert "no-progress: ok" in out
    # attempt-limit for implementation_fix (max 3) shouldn't trip with only 2 attempts
    assert "attempt-limit: TRIPPED" not in out
    assert rc == 0


def test_evidence_conflict_trips_on_missing_path(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    status = dict(BASE_STATUS)
    status["evidence_index"] = ["evidence/does-not-exist.md"]
    write_status(run_dir, status)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 1
    assert "evidence-conflict: TRIPPED" in out
    assert "does-not-exist.md" in out


def test_evidence_conflict_ok_when_paths_exist(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir()
    (evidence_dir / "ev.md").write_text("proof")
    status = dict(BASE_STATUS)
    status["evidence_index"] = ["evidence/ev.md"]
    write_status(run_dir, status)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert "evidence-conflict: ok" in out
    assert rc == 0


def test_gate_encountered_trips_with_informational_message(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    status = dict(BASE_STATUS)
    status["gate"] = {"id": "merge", "question": "Approve merging this PR?"}
    write_status(run_dir, status)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 1
    assert "gate-encountered: TRIPPED" in out
    assert "correctly stopped at gate" in out


def test_handoff_insufficient_trips_on_missing_section(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    incomplete = VALID_HANDOFF.replace("## Escalation\nNone.\n", "")
    (run_dir / "handoff.md").write_text(incomplete)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 1
    assert "handoff-insufficient: TRIPPED" in out
    assert "Escalation" in out


def test_handoff_missing_entirely_is_not_checked(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert "handoff-insufficient" not in out
    assert rc == 0


def test_all_clear_status_exits_zero(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 0
    assert "PASS breaker-check" in out


def test_valid_handoff_does_not_trip(tmp_path):
    repo_root = make_repo_root(tmp_path)
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    (run_dir / "handoff.md").write_text(VALID_HANDOFF)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 0
    assert "handoff-insufficient: ok" in out


def test_budget_limits_absent_is_silently_skipped(tmp_path):
    repo_root = make_repo_root(tmp_path, budget_limits=None)
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root),
                             "--ticket", "SALON-1"])
    assert rc == 0
    assert "budget-exceeded" not in out


def test_budget_limits_present_but_no_ticket_is_skipped(tmp_path):
    repo_root = make_repo_root(tmp_path, budget_limits={"defaults": {"ceiling_usd": 10}})
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root)])
    assert rc == 0
    assert "budget-exceeded" not in out


def test_budget_limits_present_with_ticket_but_metrics_tool_missing_skips(tmp_path):
    # repo_root has no tools/agent-metrics/metrics.py at all -> subprocess fails.
    repo_root = make_repo_root(tmp_path, budget_limits={"defaults": {"ceiling_usd": 10}})
    run_dir = make_run_dir(tmp_path)
    write_status(run_dir, BASE_STATUS)
    rc, out, err = run_cli(["--run-dir", str(run_dir), "--repo-root", str(repo_root),
                             "--ticket", "SALON-1"])
    assert rc == 0
    assert "budget-exceeded: SKIP" in out


def test_help_exits_zero():
    rc, out, err = run_cli(["--help"])
    assert rc == 0
    assert "breaker-check" in out


def test_missing_run_dir_arg_exits_two():
    rc, out, err = run_cli([])
    assert rc == 2
