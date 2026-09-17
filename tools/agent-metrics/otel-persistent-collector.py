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
                # Claude Code puts session.id on the DATA POINT's own attributes, not the
                # resource's, unlike a typical OTel resource attribute - confirmed against a
                # real export from claude-code 2.1.273. Resource attrs are still checked as a
                # fallback in case that ever changes or another exporter differs.
                session = attrs.get("session.id") or res_attrs.get("session.id") or "unknown"
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


class SingleInstanceHTTPServer(ThreadingHTTPServer):
    """`socketserver.TCPServer.allow_reuse_address` defaults to True, and on WINDOWS
    (unlike POSIX, where it mainly just skips TIME_WAIT) that lets a second process bind
    to a port another process is already actively listening on - both "succeed" with no
    error, and the OS silently splits traffic between them. Confirmed the hard way: a
    `SessionStart` hook firing on several session resumes left five collector processes all
    "listening" on 4318 at once, invisible to `already_listening()`'s own connect probe
    (which just confirms *something* answers, not that autostart's own check-then-spawn is
    exclusive). Disabling it here makes a real conflict fail loudly - address already in
    use - which is what should happen when a collector is already running.
    """
    allow_reuse_address = False


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

    srv = SingleInstanceHTTPServer(("127.0.0.1", port), Handler)
    print(f"listening on http://127.0.0.1:{port}  (Ctrl+C to stop)")
    print(f"writing to {out_path}")
    print("point Claude Code sessions at this with OTEL_EXPORTER_OTLP_ENDPOINT="
          f"http://127.0.0.1:{port} and CLAUDE_CODE_ENABLE_TELEMETRY=1")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def collect(in_path: Path, by: str, since: str | None,
            session: str | None) -> list[dict]:
    """Group logged rows by `by` (optionally restricted to one `session`), and return one
    dict per group with cost_usd and the four token metrics summed, plus total_tokens
    derived. Used by both the text and JSON report renderers, and by a caller (e.g. an
    SDLC skill) that wants the numbers for exactly one session it just ran.
    """
    if not in_path.exists():
        return []
    groups: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    with in_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if since and row["ts"][:10] < since:
                continue
            if session and row.get("session") != session:
                continue
            key = row.get(by, "-")
            g = groups[key]
            g.setdefault("session", row.get("session", "-"))
            g.setdefault("last_ts", row["ts"])
            g["last_ts"] = max(g["last_ts"], row["ts"])
            if row["metric"] == COST_METRIC:
                g["cost_usd"] += row["value"]
            else:
                metric = TOKEN_TYPES.get(row.get("type") or "")
                if metric:
                    g[metric] += row["value"]
    out = []
    for key, g in groups.items():
        total_tokens = sum(g.get(m, 0) for m in
                           ("input_tokens", "output_tokens",
                            "cache_read_tokens", "cache_creation_tokens"))
        out.append({
            by: key, "cost_usd": round(g.get("cost_usd", 0), 6),
            "total_tokens": int(total_tokens),
            "input_tokens": int(g.get("input_tokens", 0)),
            "output_tokens": int(g.get("output_tokens", 0)),
            "cache_read_tokens": int(g.get("cache_read_tokens", 0)),
            "cache_creation_tokens": int(g.get("cache_creation_tokens", 0)),
            "session": g.get("session", "-"), "last_ts": g.get("last_ts")})
    return sorted(out, key=lambda r: -r["cost_usd"])


def report(in_path: Path, by: str, since: str | None, session: str | None,
           as_json: bool) -> None:
    rows = collect(in_path, by, since, session)
    if not rows:
        if as_json:
            print("[]")
        else:
            scope = f"session={session}" if session else (f"since {since}" if since else "")
            print(f"no rows {scope} in {in_path}".strip())
        return
    if as_json:
        print(json.dumps(rows, indent=2))
        return
    for r in rows:
        print(f"{by}={r[by]:<24}  cost_usd={r['cost_usd']:.4f}  "
              f"total_tokens={r['total_tokens']}  "
              f"input={r['input_tokens']}  output={r['output_tokens']}  "
              f"cache_read={r['cache_read_tokens']}  "
              f"cache_creation={r['cache_creation_tokens']}")


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

        # session.id lives on the DATA POINT's own attributes in a real Claude Code export
        # (confirmed against a live 2.1.273 capture) - NOT on the resource, unlike a typical
        # OTel resource attribute. Every test below puts it there to match reality.
        n = ledger.ingest(_body([
            (COST_METRIC, {"model": "opus-5", "query_source": "subagent",
                           "agent.name": "test", "session.id": "sess-a"}, 0.018),
            (TOKEN_METRIC, {"model": "opus-5", "query_source": "subagent",
                            "agent.name": "test", "session.id": "sess-a",
                            "type": "output"}, 400),
        ]))
        check("ingest returns the row count it wrote", n == 2)
        check("output file created", out.exists())

        n2 = ledger.ingest(_body([
            (COST_METRIC, {"model": "opus-5", "query_source": "main",
                           "session.id": "sess-b"}, 0.5)]))
        check("a second, concurrent session is kept separate", n2 == 1)

        lines = out.read_text(encoding="utf-8").splitlines()
        check("one line per accepted delta", len(lines) == 3)
        rows = [json.loads(l) for l in lines]
        check("session id read from the data point's own attributes",
              {r["session"] for r in rows} == {"sess-a", "sess-b"})

        # Resource-level session.id is a fallback only (kept in case some other exporter
        # puts it there), never the primary source - so it must lose to a data point value.
        n_fallback = ledger.ingest(_body(
            [(COST_METRIC, {"model": "opus-5", "query_source": "main"}, 0.1)],
            resource_attrs={"session.id": "sess-from-resource"}))
        check("falls back to resource attrs when the data point has no session.id",
              n_fallback == 1 and json.loads(out.read_text(encoding="utf-8")
                                             .splitlines()[-1])["session"] == "sess-from-resource")

        # DELTA export from the same session ADDS, not replaces.
        ledger.ingest(_body([(COST_METRIC, {"model": "opus-5", "query_source": "subagent",
                                            "agent.name": "test",
                                            "session.id": "sess-a"}, 0.031)]))
        report(out, "session", None, None, False)  # exercise the report path; visual check
        check("session filter isolates one session's rows",
              {r["session"] for r in collect(out, "agent", None, "sess-a")} == {"sess-a"})
        json_rows = collect(out, "agent", None, "sess-a")
        check("collect() returns a per-agent breakdown for one session",
              any(r["agent"] == "test" for r in json_rows))

        # Negative: an unrelated metric produces no row.
        n3 = ledger.ingest(_body([("claude_code.session.count",
                                   {"session.id": "sess-a"}, 1)]))
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
                                                     "agent.name": "reviewer",
                                                     "session.id": "sess-live"}, 0.5)])).encode()
            urllib.request.urlopen(urllib.request.Request(
                f"http://127.0.0.1:{port}/v1/metrics", data=data,
                headers={"Content-Type": "application/json"}), timeout=5).read()
            check("live receiver ingests a real POST",
                  "sess-live" in srv_ledger.out_path.read_text(encoding="utf-8"))
        finally:
            live.shutdown()

        # A second bind to the SAME port a real collector already holds must fail loudly,
        # not silently succeed (the Windows allow_reuse_address hazard this class exists for).
        first = SingleInstanceHTTPServer(("127.0.0.1", 0), Handler)
        try:
            bound_port = first.server_port
            try:
                SingleInstanceHTTPServer(("127.0.0.1", bound_port), Handler)
                check("a second bind to an already-listening port is rejected", False)
            except OSError:
                check("a second bind to an already-listening port is rejected", True)
        finally:
            first.server_close()

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
    pr.add_argument("--session", default=None,
                    help="restrict to one session id (e.g. $CLAUDE_CODE_SESSION_ID); "
                         "combine with --by agent for a per-agent breakdown of just it")
    pr.add_argument("--json", action="store_true")
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
        report(args.in_path, args.by, args.since, args.session, args.json)
        return 0
    if args.cmd == "autostart":
        autostart(args.port, args.out, args.log)
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
