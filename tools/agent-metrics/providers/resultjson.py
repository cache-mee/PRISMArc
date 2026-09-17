#!/usr/bin/env python3
r"""Provider: cost, duration and turns from a coding agent's own result JSON.

    resultjson.py capabilities
    resultjson.py collect --request <file.json>
    resultjson.py --self-test

PHASE: parse. It owns no process. It reads the child stdout that the wrap provider
captured, and lifts the numbers the tool itself reported.

WHY IT EXISTS ALONGSIDE `otel`

    They disagree usefully. `otel` measures the whole session as it runs, split by agent;
    this reads what the tool declared at the end, for the session as a whole. When the two
    disagree the run is worth looking at - a gap means an export was lost, and a silent
    gap is how a cost report becomes fiction.

    It is also the only one of the two that works when telemetry could not be captured at
    all, which is why it is a separate provider and not a branch inside `otel`.

WHAT IT REFUSES TO GUESS

    If the output is not the tool's result JSON, it reports nothing. IT NEVER PRICES TOKENS
    ITSELF: a hardcoded price table goes stale silently, turning a missing number into a
    wrong one. Absence is reported as absence.

FIELD NAMES ARE PER TOOL, AND THAT IS THE EXTENSION POINT

    `EXTRACTORS` maps one tool's result shape to the canonical metric names. Adding another
    coding agent is a dict entry, not a code path. Only Claude Code's shape is verified here;
    anything unverified stays out rather than being guessed at.

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
import sys
from pathlib import Path

NAME = "resultjson"
PHASE = "parse"
PROVIDES = ["cost_usd", "execution_ms", "api_ms", "turns", "input_tokens",
            "output_tokens", "cache_read_tokens", "cache_creation_tokens", "total_tokens"]

# tool -> (marker key that identifies its shape, {canonical: path-in-object})
EXTRACTORS = {
    "claude-code": {
        "marker": "total_cost_usd",
        "fields": {
            "cost_usd": ("total_cost_usd",),
            "execution_ms": ("duration_ms",),
            "api_ms": ("duration_api_ms",),
            "turns": ("num_turns",),
            # `modelUsage`, NOT `usage`. `usage` is the LAST TURN only, while
            # `total_cost_usd` is the whole session - so on any multi-turn run the two
            # describe different scopes, and a cost-per-token check against them is
            # nonsense. Measured: a 28-turn run agreed exactly under `modelUsage` and was
            # out by 100x under `usage`.
            "input_tokens": ("modelUsage", "*", "inputTokens"),
            "output_tokens": ("modelUsage", "*", "outputTokens"),
            "cache_read_tokens": ("modelUsage", "*", "cacheReadInputTokens"),
            "cache_creation_tokens": ("modelUsage", "*", "cacheCreationInputTokens"),
        },
        "model": ("modelUsage",),
        "session": ("session_id",),
    },
}


def dig(obj, path):
    """Walk a path. `*` sums the key across every entry of a dict-of-dicts.

    `modelUsage` is keyed by model id, so a session that used two models has two entries;
    summing is the only reading that matches the single `total_cost_usd` beside it.
    """
    for i, key in enumerate(path):
        if not isinstance(obj, dict):
            return None
        if key == "*":
            rest = path[i + 1:]
            vals = [dig(v, rest) for v in obj.values()]
            vals = [v for v in vals if isinstance(v, (int, float))]
            return sum(vals) if vals else None
        obj = obj.get(key)
    return obj


def find_result(stdout: str) -> dict | None:
    """The last JSON object on stdout that any extractor recognises. Silent when none."""
    for line in reversed((stdout or "").strip().splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and any(spec["marker"] in obj for spec in EXTRACTORS.values()):
            return obj
    return None


def collect(req: dict) -> list[dict]:
    path = req.get("stdout_file")
    if not path or not Path(path).exists():
        return []
    obj = find_result(Path(path).read_text(encoding="utf-8", errors="replace"))
    if obj is None:
        return []
    tool, spec = next((t, s) for t, s in EXTRACTORS.items() if s["marker"] in obj)
    row = {"provider": NAME, "tool": tool, "agent": "*", "query_source": "*",
           "model": next(iter(dig(obj, spec["model"]) or {}), None),
           "session_id": dig(obj, spec["session"])}
    for canonical, path_ in spec["fields"].items():
        val = dig(obj, path_)
        if val is not None:
            row[canonical] = val
    toks = [row.get(k) for k in ("input_tokens", "output_tokens",
                                 "cache_read_tokens", "cache_creation_tokens")]
    if any(t is not None for t in toks):
        row["total_tokens"] = sum(t or 0 for t in toks)
    return [row]


# ---------------------------------------------------------------------- self-test

def self_test() -> int:
    import tempfile
    fails = []

    def check(name, cond):
        print(f"    {'ok  ' if cond else 'FAIL'}  {NAME}: {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as td:
        so, out = Path(td) / "child.out", Path(td) / "o.json"
        real = {"total_cost_usd": 0.0258402, "duration_ms": 6460, "duration_api_ms": 4977,
                "num_turns": 1, "session_id": "1598da91",
                "usage": {"input_tokens": 10, "output_tokens": 41,
                          "cache_read_input_tokens": 17982,
                          "cache_creation_input_tokens": 11442},
                "modelUsage": {"claude-haiku-4-5-20251001": {
                    "inputTokens": 909, "outputTokens": 51,
                    "cacheReadInputTokens": 17982, "cacheCreationInputTokens": 11442}}}

        so.write_text("some chatter\n" + json.dumps(real) + "\n", encoding="utf-8")
        r = collect({"stdout_file": str(so), "out": str(out)})[0]
        check("cost lifted from result JSON", r["cost_usd"] == 0.0258402)
        check("duration lifted", r["execution_ms"] == 6460)
        check("api time kept distinct from wall clock", r["api_ms"] == 4977)
        check("model lifted", r["model"] == "claude-haiku-4-5-20251001")
        check("cache tokens mapped to canonical names", r["cache_read_tokens"] == 17982)
        check("tokens read from modelUsage, not last-turn usage", r["input_tokens"] == 909)
        check("total_tokens derived across all four types", r["total_tokens"] == 30384)

        # Two models in one session must SUM, not pick one.
        two = dict(real, modelUsage={"a": {"inputTokens": 100, "outputTokens": 1,
                                           "cacheReadInputTokens": 0,
                                           "cacheCreationInputTokens": 0},
                                     "b": {"inputTokens": 50, "outputTokens": 2,
                                           "cacheReadInputTokens": 0,
                                           "cacheCreationInputTokens": 0}})
        so.write_text(json.dumps(two), encoding="utf-8")
        check("two models in one session are summed",
              collect({"stdout_file": str(so)})[0]["input_tokens"] == 150)
        check("turns lifted", r["turns"] == 1)

        # NEGATIVE: output that is not result JSON yields nothing, and invents no cost.
        so.write_text("just some text\nnot json at all\n", encoding="utf-8")
        check("no row invented from non-JSON output", collect({"stdout_file": str(so)}) == [])

        # NEGATIVE: valid JSON that is not a result object is not a result.
        so.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
        check("unrecognised JSON object ignored", collect({"stdout_file": str(so)}) == [])

        # NEGATIVE: a missing stdout file is absence, not a crash.
        check("missing stdout file reports nothing",
              collect({"stdout_file": str(Path(td) / "nope")}) == [])

        # NEGATIVE: a result missing its usage block still reports what it does have.
        so.write_text(json.dumps({"total_cost_usd": 1.5}), encoding="utf-8")
        r = collect({"stdout_file": str(so)})[0]
        check("partial result reports what exists, omits what does not",
              r["cost_usd"] == 1.5 and "total_tokens" not in r)

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
                          "dimensions": ["model"]}))
        return 0
    if a.cmd == "collect":
        req = json.loads(Path(a.request).read_text(encoding="utf-8"))
        Path(req["out"]).write_text(json.dumps({"rows": collect(req)}), encoding="utf-8")
        return 0
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
