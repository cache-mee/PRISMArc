#!/usr/bin/env python3
r"""Provider: tokens, cost and time, per agent and per model, from Claude Code's own telemetry.

    otel.py capabilities
    otel.py wrap --request <file.json> -- <command...>
    otel.py --self-test

PHASE: wrap. It owns the child process, because it is the only phase that can set the
child's environment - and pointing the child at a receiver is the whole mechanism.

WHY THIS IS THE ONLY WAY TO SPLIT BY AGENT

    A wrapped command is one process. Timing it can never separate an orchestrator from the
    delegates it spawns, because they are the same process. Claude Code's OTLP export can:
    every `claude_code.cost.usage` and `claude_code.token.usage` data point carries `model`,
    `query_source` (main / subagent / auxiliary) and, for a subagent, `agent.name`.

    Nothing else carries that. Transcripts do not - subagent turns are not written to the
    parent transcript, and `subagent_type` appears only inside the Task tool's input, never
    joined to a usage block.

NO COLLECTOR REQUIRED

    Consuming OTLP normally means running one. It does not have to. This starts a throwaway
    receiver on a loopback port for the lifetime of the child and shuts it down after.
    `OTEL_EXPORTER_OTLP_PROTOCOL=http/json` is why that is small: the payload is JSON, so
    the receiver is `http.server` and `json.loads`, with no protobuf and no dependency.

EVERY NUMBER IS REPORTED, NEVER RECONSTRUCTED

    The agent name, the model id and the dollar amount come off the same data point, so the
    cost is the one Claude Code computed for the model it actually used. There is no price
    table in this file, deliberately: a hardcoded one goes stale silently, which turns a
    missing number into a wrong one.

IT WILL NOT HIJACK AN EXISTING SETUP

    If the environment already points at a collector, this leaves it alone and reports
    `skipped`, rather than silently stealing telemetry the machine was configured to send
    somewhere else.

TEMPORALITY DECIDES WHETHER TO ADD OR TO REPLACE, AND GETTING IT WRONG IS SILENT

    Claude Code exports DELTA temporality: each data point is what was spent SINCE the last
    export, not a running total. Deltas must be ADDED. Treating them as a cumulative counter
    - taking the newest value per attribute set - looks entirely reasonable, produces
    plausible numbers, and discards every export but the last.

    Nothing about the output reveals that. There is no error, no gap, no warning; the totals
    are simply too small, and only a comparison against an independent figure catches it.
    So the temporality on the wire decides, both paths are implemented, and both have a
    self-test. This is the single most dangerous line in this file.

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
import gzip
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

NAME = "otel"
PHASE = "wrap"
COST_METRIC = "claude_code.cost.usage"
TOKEN_METRIC = "claude_code.token.usage"
PROVIDES = ["input_tokens", "output_tokens", "total_tokens", "cache_read_tokens",
            "cache_creation_tokens", "cost_usd", "execution_ms"]
CONFLICT_VARS = ("OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")

# Claude Code's token `type` attribute -> our canonical metric name.
TOKEN_TYPES = {"input": "input_tokens", "output": "output_tokens",
               "cacheRead": "cache_read_tokens", "cacheCreation": "cache_creation_tokens"}


def otlp_value(v):
    if not isinstance(v, dict):
        return None
    for k, cast in (("stringValue", str), ("intValue", int),
                    ("doubleValue", float), ("boolValue", bool)):
        if k in v:
            try:
                return cast(v[k])
            except (TypeError, ValueError):
                return None
    return None


def otlp_attrs(kvs) -> dict:
    return {kv.get("key"): otlp_value(kv.get("value"))
            for kv in (kvs or []) if isinstance(kv, dict) and kv.get("key")}


# OTLP AggregationTemporality. Claude Code exports DELTA - each data point is the amount
# spent SINCE the last export, not a running total - so points must be ADDED. Taking the
# last value instead, which is right for a cumulative counter, silently discards every
# export but the final one. Both are handled; the temporality on the wire decides which.
DELTA, CUMULATIVE = 1, 2


def otlp_points(payload: dict):
    for rm in payload.get("resourceMetrics") or []:
        for sm in rm.get("scopeMetrics") or []:
            for metric in sm.get("metrics") or []:
                body = metric.get("sum") or metric.get("gauge") or {}
                temporality = body.get("aggregationTemporality", DELTA)
                for dp in body.get("dataPoints") or []:
                    val = dp.get("asDouble")
                    if val is None and dp.get("asInt") is not None:
                        try:
                            val = float(dp["asInt"])
                        except (TypeError, ValueError):
                            continue
                    if val is not None:
                        yield (metric.get("name"), otlp_attrs(dp.get("attributes")),
                               float(val), temporality)


class Collector:
    """Last value per (metric, attribute-set). See COUNTERS ARE CUMULATIVE."""

    def __init__(self):
        self.seen: dict[tuple, float] = {}
        self.samples: list[dict] = []
        self.lock = threading.Lock()

    def ingest(self, payload: dict) -> None:
        """Record the new total, and keep a timestamped trail of every CHANGE.

        The trail is what makes per-step cost possible. A cumulative counter only says what
        an agent has spent in total; subtracting the value at one moment from the value at
        another is the only way to ask what it spent BETWEEN them - which is what a step is.
        Unchanged values are not appended, so an idle agent costs no rows.
        """
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.lock:
            for name, attrs, val, temporality in otlp_points(payload):
                if name not in (COST_METRIC, TOKEN_METRIC):
                    continue
                key = (name, tuple(sorted(attrs.items())))
                if temporality == CUMULATIVE:
                    delta = val - self.seen.get(key, 0.0)
                    self.seen[key] = val
                else:
                    delta = val
                    self.seen[key] = self.seen.get(key, 0.0) + val
                if not delta:
                    continue
                self.samples.append({
                    "ts": now, "metric": name, "value": round(delta, 9),
                    "agent": attrs.get("agent.name") or "—",
                    "model": attrs.get("model") or "—",
                    "query_source": attrs.get("query_source") or "—",
                    "type": attrs.get("type")})

    def rows(self) -> list[dict]:
        groups: dict[tuple, dict] = {}
        with self.lock:
            items = list(self.seen.items())
        for (name, attr_items), val in items:
            a = dict(attr_items)
            key = (a.get("agent.name") or "—", a.get("model") or "—",
                   a.get("query_source") or "—")
            row = groups.setdefault(key, {"provider": NAME, "agent": key[0], "model": key[1],
                                          "query_source": key[2]})
            if name == COST_METRIC:
                row["cost_usd"] = round(row.get("cost_usd", 0.0) + val, 6)  # running total
            else:
                metric = TOKEN_TYPES.get(a.get("type") or "", None)
                if metric:
                    row[metric] = int(row.get(metric, 0) + val)
        for row in groups.values():
            row["total_tokens"] = sum(row.get(m, 0) for m in
                                      ("input_tokens", "output_tokens",
                                       "cache_read_tokens", "cache_creation_tokens"))
        return sorted(groups.values(), key=lambda r: -(r.get("cost_usd") or 0))


def start_receiver(collector: Collector):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):                                     # noqa: N802
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if (self.headers.get("Content-Encoding") or "").lower() == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    raw = b""
            try:
                collector.ingest(json.loads(raw.decode("utf-8")))
            except (ValueError, UnicodeDecodeError):
                pass                                           # a bad body costs that body
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *_a):
            return

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_port


def child_env(port: int) -> dict:
    env = dict(os.environ)
    env.update({"CLAUDE_CODE_ENABLE_TELEMETRY": "1", "OTEL_METRICS_EXPORTER": "otlp",
                "OTEL_LOGS_EXPORTER": "none", "OTEL_TRACES_EXPORTER": "none",
                "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json",
                "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{port}",
                "OTEL_METRIC_EXPORT_INTERVAL": "1000"})
    # A corporate HTTP_PROXY / HTTPS_PROXY is commonly set machine-wide, and an exporter that
    # honours it will send this loopback POST to the proxy, where it vanishes. Extend NO_PROXY
    # rather than replacing it - the user's other exclusions still matter.
    existing = env.get("NO_PROXY") or env.get("no_proxy") or ""
    parts = [x for x in existing.split(",") if x.strip()]
    for host in ("127.0.0.1", "localhost", "::1"):
        if host not in parts:
            parts.append(host)
    env["NO_PROXY"] = env["no_proxy"] = ",".join(parts)
    return env


def cmd_wrap(req: dict, command: list[str], drain: float = 2.0) -> int:
    conflict = next((v for v in CONFLICT_VARS if os.environ.get(v)), None)
    collector = srv = env = None
    if not conflict:
        collector = Collector()
        srv, port = start_receiver(collector)
        env = child_env(port)

    stdout_file = req.get("stdout_file")
    sink = open(stdout_file, "w", encoding="utf-8", newline="\n") if stdout_file else None
    t0 = time.monotonic()
    # The caller resolves the command, but this provider is runnable on its own, so it must
    # not depend on that having happened.
    if command and not Path(command[0]).is_absolute():
        found = shutil.which(command[0])
        if found:
            command = ([os.environ.get("COMSPEC", "cmd.exe"), "/c", found, *command[1:]]
                       if os.name == "nt" and Path(found).suffix.lower() in (".cmd", ".bat")
                       else [found, *command[1:]])
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=None, env=env,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    for line in proc.stdout:                     # relay as it arrives; never swallow
        sys.stdout.write(line)
        sys.stdout.flush()
        if sink:
            sink.write(line)
    code = proc.wait()
    ms = int((time.monotonic() - t0) * 1000)
    if sink:
        sink.close()

    if srv is not None:
        time.sleep(drain)                        # let the child's final export land
        srv.shutdown()

    rows = collector.rows() if collector else []
    for r in rows:
        r["execution_ms"] = None                 # per-agent time is not exported; see README
    rows.append({"provider": NAME, "agent": "*", "model": "*", "query_source": "*",
                 "execution_ms": ms,
                 **({"skipped": f"{conflict} already set"} if conflict else {})})
    if collector:
        rows += [{"provider": NAME, "kind": "sample", **s} for s in collector.samples]
    Path(req["out"]).write_text(json.dumps({"rows": rows}), encoding="utf-8")
    return code


# ---------------------------------------------------------------------- self-test

def _body(points, temporality=DELTA):
    metrics = {}
    for name, attrs, val in points:
        metrics.setdefault(name, []).append(
            {"attributes": [{"key": k, "value": {"stringValue": str(v)}}
                            for k, v in attrs.items()], "asDouble": val})
    return {"resourceMetrics": [{"scopeMetrics": [{"metrics": [
        {"name": n, "sum": {"dataPoints": d, "isMonotonic": True,
                            "aggregationTemporality": temporality}}
        for n, d in metrics.items()]}]}]}


def self_test() -> int:
    fails = []

    def check(name, cond):
        print(f"    {'ok  ' if cond else 'FAIL'}  {NAME}: {name}")
        if not cond:
            fails.append(name)

    c = Collector()
    c.ingest(_body([
        (COST_METRIC, {"model": "opus-5", "query_source": "main"}, 0.024),
        (COST_METRIC, {"model": "opus-5", "query_source": "subagent",
                       "agent.name": "test"}, 0.018),
        (TOKEN_METRIC, {"model": "opus-5", "query_source": "subagent",
                        "agent.name": "test", "type": "output"}, 400),
        (TOKEN_METRIC, {"model": "opus-5", "query_source": "subagent",
                        "agent.name": "test", "type": "cacheRead"}, 9000),
    ]))
    rows = {(r["agent"], r["query_source"]): r for r in c.rows()}
    check("agent name read from the data point", ("test", "subagent") in rows)
    check("per-agent cost is the reported number", rows[("test", "subagent")]["cost_usd"] == 0.018)
    check("orchestrator cost kept separate", rows[("—", "main")]["cost_usd"] == 0.024)
    check("token type mapped to canonical name",
          rows[("test", "subagent")]["output_tokens"] == 400)
    check("cache tokens kept as their own metric",
          rows[("test", "subagent")]["cache_read_tokens"] == 9000)
    check("total_tokens derived, not reported",
          rows[("test", "subagent")]["total_tokens"] == 9400)

    # THE ONE THAT MATTERS: Claude Code exports DELTA, so a second export ADDS.
    # Taking the last value here would discard every export but the final one.
    c.ingest(_body([(COST_METRIC, {"model": "opus-5", "query_source": "subagent",
                                   "agent.name": "test"}, 0.031)]))
    r2 = {(r["agent"], r["query_source"]): r for r in c.rows()}
    check("delta exports are summed, not replaced",
          abs(r2[("test", "subagent")]["cost_usd"] - 0.049) < 1e-9)

    # And the other temporality still behaves as a running total.
    cc = Collector()
    for v in (1.0, 3.0, 7.0):
        cc.ingest(_body([(COST_METRIC, {"model": "m", "query_source": "main"}, v)],
                        temporality=CUMULATIVE))
    check("cumulative exports are not double-counted",
          abs(cc.rows()[0]["cost_usd"] - 7.0) < 1e-9)
    check("cumulative samples record the increment, not the total",
          [round(s["value"], 6) for s in cc.samples] == [1.0, 2.0, 4.0])

    # NEGATIVE: an unrelated metric must not become a row.
    c.ingest(_body([("claude_code.session.count", {"model": "zzz"}, 1)]))
    check("unrelated metric ignored", all(r["model"] != "zzz" for r in c.rows()))

    # NEGATIVE: malformed OTLP must not raise.
    try:
        c.ingest({"resourceMetrics": [{"scopeMetrics": [{"metrics": [{"name": COST_METRIC}]}]}]})
        check("malformed body ignored without raising", True)
    except Exception:
        check("malformed body ignored without raising", False)

    # The receiver really accepts a POST.
    coll = Collector()
    srv, port = start_receiver(coll)
    try:
        import urllib.request
        data = json.dumps(_body([(COST_METRIC, {"model": "m", "query_source": "subagent",
                                                "agent.name": "reviewer"}, 0.5)])).encode()
        urllib.request.urlopen(urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/metrics", data=data,
            headers={"Content-Type": "application/json"}), timeout=5).read()
        check("receiver ingests a live POST",
              any(r["agent"] == "reviewer" for r in coll.rows()))
        check("child env asks for http/json, not protobuf",
              child_env(port)["OTEL_EXPORTER_OTLP_PROTOCOL"] == "http/json")
        check("loopback excluded from any proxy",
              all(h in child_env(port)["NO_PROXY"] for h in ("127.0.0.1", "localhost")))
        os.environ["NO_PROXY"] = "example.com"
        try:
            check("an existing NO_PROXY is extended, not replaced",
                  "example.com" in child_env(port)["NO_PROXY"]
                  and "127.0.0.1" in child_env(port)["NO_PROXY"])
        finally:
            del os.environ["NO_PROXY"]
    finally:
        srv.shutdown()
    c2 = Collector()
    c2.ingest(_body([(COST_METRIC, {"model": "m", "query_source": "subagent",
                                    "agent.name": "developer"}, 1.0)]))
    n_after_first = len(c2.samples)
    c2.ingest(_body([(COST_METRIC, {"model": "m", "query_source": "subagent",
                                    "agent.name": "developer"}, 0.0)]))
    check("a zero-value export appends no sample", len(c2.samples) == n_after_first)
    c2.ingest(_body([(COST_METRIC, {"model": "m", "query_source": "subagent",
                                    "agent.name": "developer"}, 3.5)]))
    check("each delta export appends one timestamped sample",
          len(c2.samples) == n_after_first + 1)
    check("sample carries agent, model and the increment",
          c2.samples[-1]["agent"] == "developer" and c2.samples[-1]["value"] == 3.5
          and "ts" in c2.samples[-1])
    check("samples sum to the running total",
          abs(sum(s["value"] for s in c2.samples) - c2.rows()[0]["cost_usd"]) < 1e-9)

    print(f"    {NAME}: {'PASS' if not fails else 'FAIL'}")
    return 1 if fails else 0


def main() -> int:
    p = argparse.ArgumentParser(prog=f"{NAME}.py")
    p.add_argument("--self-test", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("capabilities")
    w = sub.add_parser("wrap")
    w.add_argument("--request", required=True)
    w.add_argument("--drain", type=float, default=2.0)
    w.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()

    if a.self_test:
        return self_test()
    if a.cmd == "capabilities":
        print(json.dumps({"name": NAME, "phase": PHASE, "provides": PROVIDES,
                          "dimensions": ["agent", "model", "query_source"]}))
        return 0
    if a.cmd == "wrap":
        cmd = a.command[1:] if a.command and a.command[0] == "--" else a.command
        if not cmd:
            raise SystemExit("nothing to wrap: put the command after --")
        return cmd_wrap(json.loads(Path(a.request).read_text(encoding="utf-8")), cmd, a.drain)
    p.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
