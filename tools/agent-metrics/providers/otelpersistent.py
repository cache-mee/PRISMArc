#!/usr/bin/env python3
r"""Provider: cost and tokens for sessions the throwaway `otel` provider cannot see, read
back from the persistent collector's own log.

    otelpersistent.py capabilities
    otelpersistent.py collect --request <file.json>      # request may carry {"until": <iso>}
    otelpersistent.py --self-test

PHASE: query. It reads a durable artifact - the persistent collector's log - and needs no
child process at all.

WHY THIS EXISTS

    `otel.py` starts a throwaway receiver for the lifetime of ONE wrapped child, and
    deliberately refuses to start it at all when the environment already points at a
    collector - see its own "IT WILL NOT HIJACK AN EXISTING SETUP" note. That is exactly the
    situation `otel-persistent-collector.py serve` creates: it is meant to sit under a
    project's `.claude/settings.json` OTEL_* env vars and capture every session on the
    machine, because a project-wide setting has no single child to wrap.

    That collector writes its own log - `~/.claude/metrics/otel-sessions.jsonl` by default -
    and its own docstring says plainly: "This is NOT agent-metrics' own ledger and `metrics
    report` will not read it." That was true, and is what made `metrics task` report "not
    measured" for a ticket whose whole SDLC workflow ran through sessions only the
    persistent collector could see. This file is the bridge that was missing: it reads that
    log and hands back rows in the exact shape `otel.py`'s own wrap-phase samples use, so
    `metrics task` can join them with the same `cost_in_window` logic, unchanged.

THE SENTINEL TRAP - GETTING THIS WRONG DROPS ORCHESTRATOR SPEND SILENTLY

    `otel.py` marks "no agent name on this data point" with an em dash, `"—"`, and
    `cost_in_window`'s attribution checks for exactly that sentinel before falling back to
    `query_source == "main"` for the orchestrator's own turns. The persistent collector marks
    the same absence with a plain hyphen, `"-"` (see its own `Ledger.ingest`). Passed through
    unchanged, `"-"` reads as a REAL agent name that happens to be called "-", every
    orchestrator sample fails the agent-name check, falls through to nothing, and the
    orchestrator's own spend vanishes from the report with no error and no gap - the exact
    failure mode `otel.py` documents for OTLP temporality, just one layer up. `_norm` below
    exists solely to close that gap; the self-test proves it closes it.

WHAT THIS CANNOT DO, AND WHY THAT IS NOT A BUG IN THIS FILE

    The persistent log carries no ticket, task or owner label - it is captured before
    `metrics` ever sees the session, so there is nothing to label it with. Attribution here is
    therefore time-window and agent-name only, exactly like `cost_in_window` already does for
    unlabelled ledger samples. Concretely:

      - `metrics task <record>` works: a run record supplies the window to join by.
      - `metrics report --where ticket=X` does NOT gain this data, and must not be wired to
        it: there is no window to join by outside of a run record, and no label to filter on.
        Attempting it would silently fold an unrelated concurrent session into the total.
      - A second Claude Code session on the SAME machine, active in the SAME time window as
        the one being measured, is indistinguishable from it here. Report this caveat to
        whoever reads the numbers; do not paper over it.

@author Samson Paul, samson.paul@experionglobal.com
"""

from __future__ import annotations

import sys as _sys

MIN_PYTHON = (3, 8)
if _sys.version_info < MIN_PYTHON:
    _sys.exit("agent-metrics needs Python %d.%d or newer; this is %s"
              % (MIN_PYTHON[0], MIN_PYTHON[1], _sys.version.split()[0]))

import argparse
import json
import os
import sys
from pathlib import Path

NAME = "otelpersistent"
PHASE = "query"
PROVIDES = ["input_tokens", "output_tokens", "total_tokens", "cache_read_tokens",
            "cache_creation_tokens", "cost_usd"]
COST_METRIC = "claude_code.cost.usage"
TOKEN_METRIC = "claude_code.token.usage"
DEFAULT_LOG = Path.home() / ".claude" / "metrics" / "otel-sessions.jsonl"


def default_log() -> Path:
    """Resolved at call time, like the ledger's own default - $AGENT_METRICS_OTEL_SESSIONS
    overrides it, matching the $AGENT_METRICS_LEDGER convention `metrics.py` already uses.
    """
    env = os.environ.get("AGENT_METRICS_OTEL_SESSIONS")
    return Path(env) if env else DEFAULT_LOG


def _norm(v):
    """`None`/`"-"`/`""` all mean "no name on this data point" upstream. `cost_in_window`
    only recognises the em dash for that; anything else here is misattributed silently.
    """
    return "—" if v in (None, "-", "") else v


def collect(req: dict, log_path: Path | None = None) -> list[dict]:
    path = Path(req.get("persistent_log") or "") if req.get("persistent_log") else (
        log_path or default_log())
    if not path.exists():
        return []
    until = req.get("until")
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue                     # a torn line costs that row, not the whole read
        if row.get("metric") not in (COST_METRIC, TOKEN_METRIC):
            continue
        ts = row.get("ts") or ""
        if until and ts > until:
            continue
        rows.append({"provider": NAME, "kind": "sample", "ts": ts,
                     "metric": row.get("metric"), "value": row.get("value"),
                     "agent": _norm(row.get("agent")), "model": _norm(row.get("model")),
                     "query_source": _norm(row.get("query_source")),
                     "type": row.get("type"), "session": row.get("session")})
    return rows


# ---------------------------------------------------------------------- self-test

def self_test() -> int:
    import tempfile

    fails = []

    def check(name, cond):
        print(f"    {'ok  ' if cond else 'FAIL'}  {NAME}: {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as td:
        log = Path(td) / "otel-sessions.jsonl"

        check("missing log reports nothing", collect({}, log_path=log) == [])

        lines = [
            {"ts": "2026-09-17T16:41:00+00:00", "session": "s1",
             "metric": COST_METRIC, "value": 0.02, "agent": "-", "model": "-",
             "query_source": "main", "type": None},
            {"ts": "2026-09-17T16:59:00+00:00", "session": "s1",
             "metric": COST_METRIC, "value": 0.05, "agent": "-", "model": "opus-5",
             "query_source": "subagent", "type": None},
            {"ts": "2026-09-17T16:59:00+00:00", "session": "s1",
             "metric": TOKEN_METRIC, "value": 400, "agent": "-", "model": "opus-5",
             "query_source": "subagent", "type": "output"},
            {"ts": "2026-09-18T00:00:00+00:00", "session": "s1",       # after `until`
             "metric": COST_METRIC, "value": 9.0, "agent": "-", "model": "-",
             "query_source": "main", "type": None},
        ]
        log.write_text("".join(json.dumps(r) + "\n" for r in lines)
                       + "not json at all\n" + json.dumps(
                           {"ts": "x", "metric": "claude_code.session.count", "value": 1}) + "\n",
                       encoding="utf-8")

        rows = collect({}, log_path=log)
        check("cost and token rows read back", len(rows) == 4)
        check("unrelated metric ignored", all(r["metric"] != "claude_code.session.count"
                                              for r in rows))
        check("malformed line skipped, not fatal", True)          # collect() above did not raise

        check("hyphen sentinel normalised to the em dash `cost_in_window` expects",
              all(r["agent"] == "—" for r in rows))
        check("a real model name is passed through unchanged",
              any(r["model"] == "opus-5" for r in rows))
        check("session id carried through for inspection",
              all(r["session"] == "s1" for r in rows))

        scoped = collect({"until": "2026-09-17T18:00:00+00:00"}, log_path=log)
        check("`until` excludes samples after the window", len(scoped) == 3)

        env_path = Path(td) / "elsewhere.jsonl"
        env_path.write_text(json.dumps(lines[0]) + "\n", encoding="utf-8")
        os.environ["AGENT_METRICS_OTEL_SESSIONS"] = str(env_path)
        try:
            check("$AGENT_METRICS_OTEL_SESSIONS overrides the default path",
                  len(collect({})) == 1)
        finally:
            del os.environ["AGENT_METRICS_OTEL_SESSIONS"]

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
                          "dimensions": ["agent", "model", "query_source", "session"]}))
        return 0
    if a.cmd == "collect":
        req = json.loads(Path(a.request).read_text(encoding="utf-8"))
        Path(req["out"]).write_text(json.dumps({"rows": collect(req)}), encoding="utf-8")
        return 0
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
