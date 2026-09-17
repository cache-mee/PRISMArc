#!/usr/bin/env python3
r"""Provider: what a task's run record already knows — steps, owners, rework, outcome.

    runrecord.py capabilities
    runrecord.py collect --request <file.json>      # request carries {"record": <path>}
    runrecord.py --self-test

PHASE: query. It reads a durable artifact and needs no child process at all.

WHY THIS IS A PROVIDER AND NOT A DASHBOARD FEATURE

    Rework, human intervention and task outcome cannot be derived from telemetry. No
    exporter knows that a step was attempted three times, that a person approved a gate, or
    that the run stopped rather than finished. Those are PROCESS facts, and the only place
    they exist is the run record - which already records them, by design, because a retry
    opens a new row rather than editing the old one.

    So this provider reads, and asserts nothing. It does not parse the step SEQUENCE - that
    belongs to the routing table in `.claude/agents/lead.md` - and it writes nothing back.

WHAT EACH METRIC MEANS HERE, PRECISELY

    rework                attempts beyond the first at the same step id. Two rows for step 3
                          is one rework, not two - the first attempt is the work.
    human_interventions   rows owned by `human`. A gate that was awaited and approved is ONE
                          intervention, not two, because it is one decision.
    outcome               the record's own derived State, unchanged: complete, stopped,
                          awaiting-human or active. It is not re-derived here; a second
                          implementation of a state machine is a second answer.
    build_status          from the newest `exit:<code>:` evidence, when there is one.

THE FORMAT IT READS

    A six-column table with an `Issue:` field above it. This is deliberately a SHAPE, not a
    workflow: whatever the project calls a unit of work - a ticket, a story, a Bolt - is the
    same to this file, and nothing here knows which. A row that is not six
    cells is skipped rather than guessed at, because a record this cannot read is a record
    written by something else, and inventing a reading of it would be worse than silence.

@author Samson Paul, samson.paul@experionglobal.com
"""

from __future__ import annotations

import sys as _sys

# Stated once, checked once. Python 2 never reaches this - it fails parsing an f-string
# further down - so the launcher is what produces a readable message there. This catches
# the case a launcher cannot: a Python 3 too old for what is used below.
MIN_PYTHON = (3, 8)
if _sys.version_info < MIN_PYTHON:
    _sys.exit("agent-metrics needs Python %d.%d or newer; this is %s"
              % (MIN_PYTHON[0], MIN_PYTHON[1], _sys.version.split()[0]))

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

NAME = "runrecord"
PHASE = "query"
PROVIDES = ["rework", "human_interventions", "outcome", "build_status", "steps"]

# `Issue` and `State` are what this reads; the rest are carried through if present. Extra
# names cost nothing and let a project keep its own header without a flag.
FIELD_RE = re.compile(r"^(Task|Bolt|Ticket|Story|Issue|Branch|State|Next):\s*(.*)$", re.M)
EXIT_RE = re.compile(r"^exit:(\d+):")


def parse_record(text: str) -> dict:
    text = text.replace("\r\n", "\n")
    found = {m.group(1): m.group(2).strip() for m in FIELD_RE.finditer(text)}
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|- "):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 6 or cells[0] in ("#", ""):
            continue                     # a header, or a shape this cannot read: skip, never guess
        rows.append(dict(zip(("n", "step", "owner", "outcome", "evidence", "at"), cells)))
    return {"fields": found, "rows": rows}


def step_rows(rec: dict) -> list[dict]:
    """One row per ATTEMPT, carrying the window it occupied, so cost can be joined to it."""
    rows = rec["rows"]
    attempts = Counter()
    out = []
    for i, r in enumerate(rows):
        attempts[r["n"]] += 1
        # `At` is stamped when the row COMPLETES. So the window a step occupied opens when
        # the row before it closed, and shuts at its own stamp - not the other way round.
        # Getting this backwards attributes every step's spend to the step after it.
        since = rows[i - 1]["at"] if i else None
        code = EXIT_RE.match(r["evidence"] or "")
        out.append({
            "provider": NAME, "kind": "step",
            "step": r["n"], "step_cmd": r["step"], "agent": r["owner"],
            "step_outcome": r["outcome"], "evidence": r["evidence"],
            "at": r["at"], "since": since, "attempt": attempts[r["n"]],
            **({"build_status": "pass" if code.group(1) == "0" else "fail"} if code else {}),
        })
    return out


def summary_row(rec: dict) -> dict:
    rows = rec["rows"]
    per_step = Counter(r["n"] for r in rows)
    gates = [r for r in rows if r["owner"] == "human"]
    # A gate awaited and then approved is ONE decision; count the step it sits on, not rows.
    return {"provider": NAME, "kind": "summary", "agent": "*",
            "task": next((rec["fields"].get(k) for k in ("Task", "Bolt", "Ticket", "Story")
                          if rec["fields"].get(k)), None),
            "issue": rec["fields"].get("Issue"),
            "outcome": rec["fields"].get("State"),
            "rework": sum(n - 1 for n in per_step.values()),
            "human_interventions": len({r["n"] for r in gates}),
            "steps": len(per_step)}


def collect(req: dict) -> list[dict]:
    path = req.get("record") or (req.get("labels") or {}).get("record")
    if not path or not Path(path).exists():
        return []
    rec = parse_record(Path(path).read_text(encoding="utf-8", errors="replace"))
    if not rec["rows"]:
        return []
    return [summary_row(rec)] + step_rows(rec)


# ---------------------------------------------------------------------- self-test

RECORD = """# TASK-901 — run record
<!-- Written by tools/orchestration/run-record.py. Do not edit by hand. -->

Task:   docs/tasks/TASK-901.md
Issue:  901
Branch: task-901/example
State:  awaiting-human
Next:   triage the review

| # | Step | Owner | Outcome | Evidence | At |
|---|---|---|---|---|---|
| 1 | — | lead | done | commit:aaa | 2026-09-16T09:02:14+00:00 |
| 2 | — | test | done | commit:bbb | 2026-09-16T09:04:51+00:00 |
| 3 | — | developer | failed | exit:1:npm test | 2026-09-16T09:07:00+00:00 |
| 3 | — | developer | done | commit:ccc | 2026-09-16T09:11:08+00:00 |
| 4 | npm test | test | done | exit:0:npm test | 2026-09-16T09:18:22+00:00 |
| 7 | gate triage | human | awaiting | — | 2026-09-16T09:20:00+00:00 |
"""


def self_test() -> int:
    import tempfile
    fails = []

    def check(name, cond):
        print(f"    {'ok  ' if cond else 'FAIL'}  {NAME}: {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "TASK-901.md"
        f.write_text(RECORD, encoding="utf-8")
        rows = collect({"record": str(f)})
        summary = rows[0]
        steps = [r for r in rows if r["kind"] == "step"]

        check("every attempt becomes a row", len(steps) == 6)
        check("owner is carried as the agent name", steps[1]["agent"] == "test")
        check("rework counts attempts beyond the first", summary["rework"] == 1)
        check("a retry is the same step id, not a new step", summary["steps"] == 5)
        check("second attempt numbered", steps[3]["attempt"] == 2)
        check("human gate counted as one intervention", summary["human_interventions"] == 1)
        check("outcome is the record's own State, not re-derived",
              summary["outcome"] == "awaiting-human")
        check("build status read from wrapped exit code",
              steps[4]["build_status"] == "pass" and steps[2]["build_status"] == "fail")
        check("a step's window opens when the previous row closed",
              steps[1]["since"] == steps[0]["at"] and steps[0]["since"] is None)

        # NEGATIVE: a table that is not six cells is skipped, never guessed at.
        f.write_text(RECORD.replace("| 1 | — | lead | done | commit:aaa |",
                                    "| 1 | — | lead | done |"), encoding="utf-8")
        check("row of the wrong shape skipped, not misread",
              len([r for r in collect({"record": str(f)}) if r["kind"] == "step"]) == 5)

        # NEGATIVE: a missing or empty record is absence, not a crash.
        check("missing record reports nothing", collect({"record": str(Path(td) / "no")}) == [])
        (Path(td) / "empty.md").write_text("", encoding="utf-8")
        check("empty record reports nothing",
              collect({"record": str(Path(td) / "empty.md")}) == [])
        check("no record path reports nothing", collect({}) == [])

    print(f"    {NAME}: {'PASS' if not fails else 'FAIL'}")
    return 1 if fails else 0


def main() -> int:
    p = argparse.ArgumentParser(prog=f"{NAME}.py")
    p.add_argument("--self-test", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("capabilities")
    c = sub.add_parser("collect")
    c.add_argument("--request", required=True)
    a = p.parse_args()

    if a.self_test:
        return self_test()
    if a.cmd == "capabilities":
        print(json.dumps({"name": NAME, "phase": PHASE, "provides": PROVIDES,
                          "dimensions": ["step", "agent"]}))
        return 0
    if a.cmd == "collect":
        req = json.loads(Path(a.request).read_text(encoding="utf-8"))
        Path(req["out"]).write_text(json.dumps({"rows": collect(req)}), encoding="utf-8")
        return 0
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
