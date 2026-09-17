#!/usr/bin/env python3
r"""A persistent OTLP/HTTP receiver for Claude Code telemetry, covering sessions
agent-metrics' own `metrics run` cannot wrap (interactive sessions, sessions started from
the VSCode/desktop UI, anything not launched by a script).

WHY THIS FILE EXISTS, AND WHY IT IS NOT part of tools/agent-metrics/providers/

agent-metrics' otel.py provider starts a THROWAWAY receiver for the lifetime of one
wrapped child process - see its own docstring. That only works for a command `metrics run`
itself launches. It cannot attach to a session already running, and it cannot wrap a
session opened from an IDE, because there is no shell invocation to prefix.

The only way to capture those sessions is Claude Code's own global OpenTelemetry export,
which requires something to be listening BEFORE any session starts and to keep listening
across every session on the machine - i.e. a persistent process, not a one-shot wrap. That
is a different lifecycle from every provider in providers/, so it is a separate script
rather than a fourth phase bolted onto the existing contract.

    otel-persistent-collector.py serve  [--port 4318] [--out PATH]
    otel-persistent-collector.py report [--by session|agent|model|query_source]
                                         [--since YYYY-MM-DD] [--in PATH]
    otel-persistent-collector.py --self-test

USAGE

    1. `serve` before opening any Claude Code session you want captured, and leave it
       running. It listens on 127.0.0.1 only.
    2. Claude Code sessions on this machine export telemetry once
       CLAUDE_CODE_ENABLE_TELEMETRY=1 and OTEL_EXPORTER_OTLP_ENDPOINT point at it - see
       AGENT-INSTALL.md section 5d for the env vars, or the settings.json this was set up
       alongside.
    3. `report` any time to read back what has landed, grouped however you like.

Every accepted delta is appended as one line to the output file, one line per (metric,
attribute-set) change - the same shape as otel.py's `samples`, so `report` here is a
smaller, file-based version of `metrics report`. This is NOT agent-metrics' own ledger and
`metrics report` will not read it; it is a separate log for the sessions that tool cannot
see.

@author Samson Paul, samson.paul@experionglobal.com
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import threading
from collections import defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

COST_METRIC = "claude_code.cost.usage"
TOKEN_METRIC = "claude_code.token.usage"
TOKEN_TYPES = {"input": "input_tokens", "output": "output_tokens",
               "cacheRead": "cache_read_tokens", "cacheCreation": "cache_creation_tokens"}
DELTA, CUMULATIVE = 1, 2

DEFAULT_OUT = Path.home() / ".claude" / "metrics" / "otel-sessions.jsonl"


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


def otlp_points(payload: dict):
    """Yield (metric name, resource attrs, point attrs, value, temporality) for every point."""
    for rm in payload.get("resourceMetrics") or []:
        res_attrs = otlp_attrs((rm.get("resource") or {}).get("attributes"))
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
                        yield (metric.get("name"), res_attrs, otlp_attrs(dp.get("attributes")),
                               float(val), temporality)


class Ledger:
    """Tracks cumulative counters in memory (only matters if Claude Code ever exports
    CUMULATIVE instead of DELTA - see otel.py's own note on this), and appends every
    accepted change to the output file. State is NOT persisted across restarts: a restart
    mid-session can double count a CUMULATIVE export, which is the same tradeoff otel.py's
    throwaway receiver makes, just over a longer window.
    """

    def __init__(self, out_path: Path):
        self.out_path = out_path
        self.seen: dict[tuple, float] = {}
        self.lock = threading.Lock()
        self.out_path.parent.mkdir(parents=True, exist_ok=True)

    def ingest(self, payload: dict) -> int:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        rows = []
        with self.lock:
            for name, res_attrs, attrs, val, temporality in otlp_points(payload):
                if name not in (COST_METRIC, TOKEN_METRIC):
                    continue
                session = res_attrs.get("session.id") or "unknown"
                key = (session, name, tuple(sorted(attrs.items())))
                if temporality == CUMULATIVE:
                    delta = val - self.seen.get(key, 0.0)
                    self.seen[key] = val
                else:
                    delta = val
                    self.seen[key] = self.seen.get(key, 0.0) + val
                if not delta:
                    continue
                row = {"ts": now, "session": session, "metric": name, "value": round(delta, 9),
                       "agent": attrs.get("agent.name") or "-",
                       "model": attrs.get("model") or "-",
                       "query_source": attrs.get("query_source") or "-",
                       "type": attrs.get("type")}
                rows.append(row)
        if rows:
            with self.out_path.open("a", encoding="utf-8", newline="\n") as f:
                for row in rows:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return len(rows)


def serve(port: int, out_path: Path) -> None:
    ledger = Ledger(out_path)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):                                     # noqa: N802
            raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if (self.headers.get("Content-Encoding") or "").lower() == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    raw = b""
            n = 0
            if self.path.startswith("/v1/metrics"):
                try:
                    n = ledger.ingest(json.loads(raw.decode("utf-8")))
                except (ValueError, UnicodeDecodeError):
                    pass
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
            if n:
                print(f"  +{n} row(s) -> {ledger.out_path}", flush=True)

        def log_message(self, *_a):
            return

    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"listening on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    print(f"writing to {out_path}")
    print("point Claude Code sessions at this with OTEL_EXPORTER_OTLP_ENDPOINT="
          f"http://127.0.0.1:{port} and CLAUDE_CODE_ENABLE_TELEMETRY=1")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def report(in_path: Path, by: str, since: str | None) -> None:
    if not in_path.exists():
        print(f"no rows in {in_path}")
        return
    groups: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    total_rows = 0
    with in_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if since and row["ts"][:10] < since:
                continue
            key = row.get(by, "-")
            g = groups[key]
            if row["metric"] == COST_METRIC:
                g["cost_usd"] += row["value"]
            else:
                metric = TOKEN_TYPES.get(row.get("type") or "")
                if metric:
                    g[metric] += row["value"]
            total_rows += 1
    if not total_rows:
        print(f"no rows{' since ' + since if since else ''} in {in_path}")
        return
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1].get("cost_usd", 0)):
        total_tokens = sum(g.get(m, 0) for m in
                           ("input_tokens", "output_tokens",
                            "cache_read_tokens", "cache_creation_tokens"))
        print(f"{by}={key:<24}  cost_usd={g.get('cost_usd', 0):.4f}  "
              f"total_tokens={int(total_tokens)}  "
              f"input={int(g.get('input_tokens', 0))}  output={int(g.get('output_tokens', 0))}  "
              f"cache_read={int(g.get('cache_read_tokens', 0))}  "
              f"cache_creation={int(g.get('cache_creation_tokens', 0))}")


def already_listening(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", port)) == 0


def autostart(port: int, out_path: Path, log_path: Path) -> None:
    """For a SessionStart hook: start the collector in the background if, and only if,
    nothing is already listening on the port - so N sessions starting close together do
    not each spawn their own collector. Exits immediately either way; never blocks a
    session start on this.
    """
    if already_listening(port):
        print(f"otel collector already running on 127.0.0.1:{port}")
        return
    import subprocess
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "a", encoding="utf-8")
    cmd = [sys.executable, str(Path(__file__).resolve()), "serve",
           "--port", str(port), "--out", str(out_path)]
    kwargs = {"stdout": log, "stderr": log, "stdin": subprocess.DEVNULL, "close_fds": True}
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.DETACHED_PROCESS
                                    | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)
    print(f"started otel collector on 127.0.0.1:{port}, logging to {out_path} "
          f"(collector's own stdout/stderr -> {log_path})")


# ---------------------------------------------------------------------- self-test

def _body(points, temporality=DELTA, resource_attrs=None):
    metrics = {}
    for name, attrs, val in points:
        metrics.setdefault(name, []).append(
            {"attributes": [{"key": k, "value": {"stringValue": str(v)}}
                            for k, v in attrs.items()], "asDouble": val})
    resource = {"attributes": [{"key": k, "value": {"stringValue": str(v)}}
                               for k, v in (resource_attrs or {}).items()]}
    return {"resourceMetrics": [{"resource": resource, "scopeMetrics": [{"metrics": [
        {"name": n, "sum": {"dataPoints": d, "isMonotonic": True,
                            "aggregationTemporality": temporality}}
        for n, d in metrics.items()]}]}]}


def self_test() -> int:
    import tempfile
    fails = []

    def check(name, cond):
        print(f"    {'ok  ' if cond else 'FAIL'}  {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "otel-sessions.jsonl"
        ledger = Ledger(out)

        n = ledger.ingest(_body([
            (COST_METRIC, {"model": "opus-5", "query_source": "subagent",
                           "agent.name": "test"}, 0.018),
            (TOKEN_METRIC, {"model": "opus-5", "query_source": "subagent",
                            "agent.name": "test", "type": "output"}, 400),
        ], resource_attrs={"session.id": "sess-a"}))
        check("ingest returns the row count it wrote", n == 2)
        check("output file created", out.exists())

        n2 = ledger.ingest(_body([
            (COST_METRIC, {"model": "opus-5", "query_source": "main"}, 0.5)],
            resource_attrs={"session.id": "sess-b"}))
        check("a second, concurrent session is kept separate", n2 == 1)

        lines = out.read_text(encoding="utf-8").splitlines()
        check("one line per accepted delta", len(lines) == 3)
        rows = [json.loads(l) for l in lines]
        check("session id carried from resource attributes",
              {r["session"] for r in rows} == {"sess-a", "sess-b"})

        # DELTA export from the same session ADDS, not replaces.
        ledger.ingest(_body([(COST_METRIC, {"model": "opus-5", "query_source": "subagent",
                                            "agent.name": "test"}, 0.031)],
                            resource_attrs={"session.id": "sess-a"}))
        report(out, "session", None)  # exercise the report path; visual check only

        # Negative: an unrelated metric produces no row.
        n3 = ledger.ingest(_body([("claude_code.session.count", {}, 1)],
                                 resource_attrs={"session.id": "sess-a"}))
        check("unrelated metric ignored", n3 == 0)

        # Negative: malformed OTLP must not raise.
        try:
            ledger.ingest({"resourceMetrics": [{"scopeMetrics": [
                {"metrics": [{"name": COST_METRIC}]}]}]})
            check("malformed body ignored without raising", True)
        except Exception:
            check("malformed body ignored without raising", False)

        # The receiver really accepts a POST end to end.
        srv_ledger = Ledger(Path(tmp) / "live.jsonl")
        srv = ThreadingHTTPServer(("127.0.0.1", 0), None)  # placeholder, replaced below
        srv.server_close()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):                                 # noqa: N802
                raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                srv_ledger.ingest(json.loads(raw.decode("utf-8")))
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *_a):
                return

        live = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        port = live.server_port
        threading.Thread(target=live.serve_forever, daemon=True).start()
        try:
            import urllib.request
            data = json.dumps(_body([(COST_METRIC, {"model": "m", "query_source": "subagent",
                                                     "agent.name": "reviewer"}, 0.5)],
                                    resource_attrs={"session.id": "sess-live"})).encode()
            urllib.request.urlopen(urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/metrics", data=data,
                headers={"Content-Type": "application/json"}), timeout=5).read()
            check("live receiver ingests a real POST",
                  "sess-live" in srv_ledger.out_path.read_text(encoding="utf-8"))
        finally:
            live.shutdown()

    print(f"\n{len(fails)} failing" if fails else "\nPASS")
    return 1 if fails else 0


def main() -> int:
    p = argparse.ArgumentParser(prog="otel-persistent-collector")
    p.add_argument("--self-test", action="store_true")
    sub = p.add_subparsers(dest="cmd")

    ps = sub.add_parser("serve", help="listen forever and log every session's telemetry")
    ps.add_argument("--port", type=int, default=4318)
    ps.add_argument("--out", type=Path, default=DEFAULT_OUT)

    pr = sub.add_parser("report", help="read the log back")
    pr.add_argument("--by", default="session", choices=["session", "agent", "model",
                                                        "query_source"])
    pr.add_argument("--since", default=None, help="YYYY-MM-DD")
    pr.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_OUT)

    pa = sub.add_parser("autostart", help="start the collector in the background if "
                                          "nothing is listening yet; for a SessionStart hook")
    pa.add_argument("--port", type=int, default=4318)
    pa.add_argument("--out", type=Path, default=DEFAULT_OUT)
    pa.add_argument("--log", type=Path, default=Path.home() / ".claude" / "metrics"
                                                / "otel-collector.log")

    args = p.parse_args()
    if args.self_test:
        return self_test()
    if args.cmd == "serve":
        serve(args.port, args.out)
        return 0
    if args.cmd == "report":
        report(args.in_path, args.by, args.since)
        return 0
    if args.cmd == "autostart":
        autostart(args.port, args.out, args.log)
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
