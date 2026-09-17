#!/usr/bin/env python3
r"""Ask for metrics; this finds the providers that supply them and runs them in the right order.

    metrics.py capabilities                                  what is available, and from where
    metrics.py run --want cost_usd,total_tokens -- <cmd...>  measure a command
    metrics.py run --all -- <cmd...>                         every metric anything can supply
    metrics.py report [--by agent|model|<label>]             read the ledger back
    metrics.py tail [-n N]
    metrics.py --self-test                                   this, and every provider's own

Exit code of `run` is ALWAYS the wrapped command's own, so this composes in front of
anything without changing what the caller sees.

WHY A CALLER AND PROVIDERS, RATHER THAN ONE FILE

    One file that grows a branch per data source is a file nobody can safely delete anything
    from. Each provider here answers exactly one SOURCE - not one metric - and this file
    knows none of their internals. It discovers them by globbing a directory and asking each
    what it can do, so adding a source is dropping a file in and removing one is deleting a
    file. Nothing here changes either way.

    Splitting per METRIC would have been the wrong cut: six metrics that arrive in a single
    telemetry export are one provider, because splitting them would mean six receivers and
    six runs of your command. The boundary that matters is where a number comes from.

THE FOUR PHASES, AND WHY EXACTLY FOUR

    wrap    Owns the child process. AT MOST ONE, because only one thing can set the child's
            environment - which is the whole mechanism telemetry needs. It therefore also
            captures the child's stdout on everyone else's behalf.
    parse   Reads that captured stdout once the child has exited. Owns no process.
    around  Called twice, before and after, for state observed by looking at the world
            rather than at the process.
    query   Reads a durable artifact and needs no child at all.

    A provider declares its phase; this file never special-cases one by name. `otel` is not
    mentioned anywhere below, which is the property that makes it removable.

THE CONTRACT IS EXECUTABLE, NOT IMPORTED

    Providers are run as subprocesses and answer JSON. Nothing is imported, so a provider
    cannot corrupt this process, can be written in any language, and can be run by hand
    exactly as this runs it - which is what makes one debuggable on its own.

    Full contract: README.md beside this file.

A PROVIDER THAT FAILS IS REPORTED, NOT FATAL

    Its rows are missing and the run says so. The alternative - one broken provider taking
    down a measured run - would make measuring riskier than not measuring, and nobody would
    keep it switched on.

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
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

EXAMPLES = """examples:
  metrics run --as test -- claude -p "/write-tests"    measure an agent run
  metrics report --by owner                            what each agent cost
  metrics report --where owner=test --by model         one agent, split by model
  metrics task .tasks/TASK-42/record.md                cost per step of a task
  metrics capabilities                                 which metrics are available
  metrics --self-test                                  verify this install

the one rule:
  everything after `--` is measured; everything before it only describes how to
  file the result. `metrics run --owner test` alone measures nothing.

docs:
  AGENT-INSTALL.md   installing and integrating (written for an AI agent)
  README.md          the provider contract, for adding a data source
"""

HERE = Path(__file__).resolve().parent
PROVIDER_DIR = HERE / "providers"
def default_ledger() -> Path:
    """Where measurements land, resolved at CALL time because the answer is the repo.

    A ledger belongs to the thing being measured. Inside a git repository that is the
    repository, so the file sits at its root and the numbers travel with the project rather
    than pooling in one machine-wide pile that mixes every checkout together.

    Outside a repository there is nothing to belong to, so it falls back to the home
    directory. $AGENT_METRICS_LEDGER overrides both, and --ledger overrides that.
    """
    env = os.environ.get("AGENT_METRICS_LEDGER")
    if env:
        return Path(env)
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip()) / ".agent-metrics" / "ledger.jsonl"
    except (OSError, subprocess.SubprocessError):
        pass
    return Path.home() / ".claude" / "metrics" / "ledger.jsonl"
PHASE_ORDER = {"around": 0, "wrap": 1, "parse": 2, "query": 3}


def discover(provider_dir: Path | None = None) -> list[dict]:
    """Every provider that answers `capabilities`. One that does not is skipped, not fatal.

    The directory is resolved at CALL time, never bound as a default - a default argument
    freezes at import and cannot be pointed anywhere else, which would make this function
    untestable against anything but the real provider set.
    """
    provider_dir = Path(provider_dir or PROVIDER_DIR)
    found = []
    for path in sorted(provider_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            out = subprocess.run([sys.executable, str(path), "capabilities"],
                                 capture_output=True, text=True, timeout=20)
            cap = json.loads(out.stdout.strip())
            cap["path"] = str(path)
            found.append(cap)
        except (ValueError, OSError, subprocess.SubprocessError):
            continue
    return sorted(found, key=lambda c: (PHASE_ORDER.get(c.get("phase"), 9), c.get("name", "")))


def select(providers: list[dict], want: set[str] | None) -> list[dict]:
    """Providers needed to cover `want`. None means everything available."""
    if want is None:
        return providers
    return [p for p in providers if want & set(p.get("provides") or [])]


def _call(cap: dict, verb: str, req: dict, workdir: Path,
          command: list[str] | None = None, passthrough: bool = False) -> tuple[int, list[dict]]:
    """Run one provider. Its rows come back through a file so stdout stays the child's."""
    out = workdir / f"{cap['name']}.{req.get('when', verb)}.json"
    req = {**req, "out": str(out)}
    reqfile = workdir / f"{cap['name']}.{req.get('when', verb)}.req.json"
    reqfile.write_text(json.dumps(req), encoding="utf-8")

    argv = [sys.executable, cap["path"], verb, "--request", str(reqfile)]
    if command:
        argv += ["--"] + command
    if passthrough:
        code = subprocess.run(argv).returncode          # child's output flows to the terminal
    else:
        proc = subprocess.run(argv, capture_output=True, text=True)
        code = proc.returncode
        if code != 0 and proc.stderr:
            print(f"[metrics] provider {cap['name']} failed: "
                  f"{proc.stderr.strip().splitlines()[-1][:160]}", file=sys.stderr)
    rows = []
    if out.exists():
        try:
            rows = json.loads(out.read_text(encoding="utf-8")).get("rows") or []
        except ValueError:
            print(f"[metrics] provider {cap['name']} wrote unreadable rows", file=sys.stderr)
    return code, rows


def find_agent(name: str, start: Path | None = None) -> Path | None:
    """`.claude/agents/<name>.md`, from here upwards.

    This is a Claude Code convention, not any one project's - which is why resolving an
    agent by name belongs here and a step number does not. A step only means something
    inside a particular workflow; an agent file is in the same place in every repo.
    """
    here = (start or Path.cwd()).resolve()
    for d in [here, *here.parents]:
        candidate = d / ".claude" / "agents" / f"{name}.md"
        if candidate.is_file():
            return candidate
    return None


def resolve_command(command: list[str]) -> list[str]:
    """Turn a bare command name into something this platform can actually spawn.

    Windows `CreateProcess` - which is what `subprocess` uses - does NOT search PATHEXT and
    cannot execute a `.cmd` or `.bat` at all. Claude Code installs as `claude.cmd` there, so
    `Popen(["claude", ...])` raises `WinError 193` and the whole run dies before it starts.
    `shutil.which` does the PATHEXT search; a batch shim then has to go through the command
    interpreter. On POSIX this resolves the name and changes nothing else.
    """
    if not command:
        return command
    found = shutil.which(command[0])
    if not found:
        return command                       # let the OS raise; the message names the command
    if os.name == "nt" and Path(found).suffix.lower() in (".cmd", ".bat"):
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        return [comspec, "/c", found, *command[1:]]
    return [found, *command[1:]]


def is_claude(command: list[str]) -> bool:
    """Whether the thing being measured is Claude Code, under any of its install shapes.

    `claude`, `claude.exe`, `claude.cmd`, and an absolute path to any of them.

    Both separators are handled explicitly rather than via `Path`, because `Path` follows the
    HOST's rules: a Windows path inspected on Linux keeps its backslashes and the stem comes
    back as the whole string. Tests that behave differently per platform are worse than no
    tests, so this answers the same on every platform.
    """
    if not command:
        return False
    leaf = command[0].replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]
    return leaf.lower().rsplit(".", 1)[0] == "claude"


def show_cmd(command: list[str]) -> str:
    """A re-runnable rendering of the command, for the shell this is actually on.

    `shlex.quote` is POSIX quoting. On Windows it wraps a path in single quotes, which cmd.exe
    does not strip - so the recorded command reads as something you could paste back and
    cannot. The stdlib already has the other half; pick by platform rather than assume one.
    """
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return " ".join(shlex.quote(c) for c in command)


def parse_labels(pairs) -> dict:
    labels = {}
    for p in pairs or []:
        if "=" not in p:
            raise SystemExit(f"--label needs key=value, got: {p}")
        k, v = p.split("=", 1)
        labels[k.strip()] = v.strip()
    return labels


def cmd_run(a: argparse.Namespace) -> int:
    command = a.command[1:] if a.command and a.command[0] == "--" else a.command
    if not command:
        raise SystemExit("nothing to measure: put the command after --")

    # --as <agent>: resolve the definition, label by it, and report as it. When the measured
    # command is `claude`, also hand it the definition - which is what actually makes the
    # session that agent rather than a generic one.
    as_agent = getattr(a, "as_agent", None)
    if as_agent:
        definition = find_agent(as_agent)
        if not definition:
            raise SystemExit(
                f"no .claude/agents/{as_agent}.md from {Path.cwd()} upwards.\n"
                f"  --as names an agent definition; if you meant only to label the run, "
                f"use --owner {as_agent}")
        a.owner = a.owner or as_agent
        if is_claude(command) and "--append-system-prompt" not in command:
            command += ["--append-system-prompt",
                        definition.read_text(encoding="utf-8")]
            print(f"[metrics] running as `{as_agent}` ({definition})", file=sys.stderr)

    # Everything, unless you narrowed it. Asking for all of it is the common case, and a
    # flag you must pass to get the obvious behaviour is a flag that only ever trips people.
    want = set(filter(None, (a.want or "").split(","))) or None

    every = discover(getattr(a, "provider_dir", None))
    providers = select(every, want)
    # A --want naming nothing real selects no provider, runs the command, and records an
    # exit code - which looks like a measurement and is not one. Name the typo instead.
    if want:
        known = {m for p in every for m in p.get("provides") or []}
        unknown = sorted(want - known)
        if unknown:
            raise SystemExit(
                "--want names %s, which no provider supplies.\n  available: %s"
                % (", ".join(repr(u) for u in unknown), ", ".join(sorted(known))))
    wraps = [p for p in providers if p.get("phase") == "wrap"]
    if len(wraps) > 1:
        raise SystemExit("more than one wrap provider matched; only one can own the child: "
                         + ", ".join(p["name"] for p in wraps))

    labels = parse_labels(a.label)

    # --record links the measurement to a task with no bookkeeping from the caller: the
    # issue number is IN the record, so asking for it again is asking twice.
    record = getattr(a, "record", None)
    if record:
        issue = re.search(r"^Issue:\s*(\d+)", Path(record).read_text(encoding="utf-8",
                                                                     errors="replace"), re.M)
        if not issue:
            raise SystemExit(f"{record}: no `Issue:` field, so there is nothing to label by")
        labels.setdefault("task", issue.group(1))
    if getattr(a, "owner", None):
        # A mistyped owner is the worst kind of wrong: it is accepted, written, and then
        # silently matches nothing at report time - so the cost column reads "—" and looks
        # like a run that was never measured rather than a flag with a letter missing.
        # When the record is here, it already lists the legal owners. Check against it.
        if record:
            owners = set(re.findall(r"^\|[^|]*\|[^|]*\|\s*([^|\s][^|]*?)\s*\|",
                                    Path(record).read_text(encoding="utf-8",
                                                           errors="replace"), re.M))
            owners -= {"Owner", "—", "-", "---"}
            # WARN, never refuse. The owner of a step that has not run yet is legitimately
            # absent from the record - which is true of every step the first time it runs.
            # Refusing would block the normal case to catch the typo.
            if owners and a.owner not in owners:
                print(f"[metrics] --owner {a.owner!r} is not yet an owner in the record "
                      f"(it has: {', '.join(sorted(owners))}). Fine for a step that has not "
                      f"run; a typo here joins to nothing.", file=sys.stderr)
        labels.setdefault("owner", a.owner)
    run_id = uuid.uuid4().hex[:12]
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    collected, missing = [], []

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        base = {"want": sorted(want) if want else None, "labels": labels,
                "cwd": os.getcwd(), "stdout_file": str(work / "child.stdout")}

        for cap in [p for p in providers if p.get("phase") == "around"]:
            _, rows = _call(cap, "collect", {**base, "when": "before"}, work)
            collected += rows

        spawnable = resolve_command(command)
        if wraps:
            code, rows = _call(wraps[0], "wrap", base, work, spawnable, passthrough=True)
            collected += rows
        else:                                   # nothing needs to own the child; just run it
            code = subprocess.run(spawnable).returncode

        for cap in [p for p in providers if p.get("phase") in ("parse", "query")]:
            _, rows = _call(cap, "collect", base, work)
            if not rows:
                missing.append(cap["name"])
            collected += rows

        for cap in [p for p in providers if p.get("phase") == "around"]:
            _, rows = _call(cap, "collect", {**base, "when": "after"}, work)
            collected += rows

    rows = [{"kind": "metric", "run": run_id, "ts": stamp, "cwd": os.getcwd(),
             "labels": labels, "exit": code,
             "cmd": show_cmd(command), **r} for r in collected]
    append(a.ledger, rows)
    if missing:
        print(f"[metrics] no rows from: {', '.join(missing)}", file=sys.stderr)
    if record:
        cmd_task(argparse.Namespace(record=record, ledger=a.ledger, label_key=None,
                                    orchestrator=getattr(a, "owner", None) or "lead",
                                    provider_dir=getattr(a, "provider_dir", None)))
    return code


def append(ledger: Path, rows: list[dict]) -> None:
    """Write the rows, or say why not. NEVER raise.

    This runs after the measured command has already finished. A read-only directory, a full
    disk or a permission problem is a reason to lose the MEASUREMENT - it is not a reason to
    lose the command's result, and a tool that turns a successful build into a traceback and
    exit 1 is worse than no tool.
    """
    if not rows:
        return
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        # One buffered write, so two concurrent runs interleave whole lines at worst rather
        # than splitting one line down the middle.
        payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
        with ledger.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
    except OSError as exc:
        print(f"[metrics] could not write {ledger}: {exc}\n"
              f"[metrics] the command's own result is unaffected.", file=sys.stderr)


def read_rows(ledger: Path) -> list[dict]:
    if not ledger.exists():
        return []
    rows = []
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue            # a torn line costs that row, not the report
    return rows


def dim_of(row: dict, dim: str) -> str:
    if dim == "project":
        return os.path.basename(row.get("cwd") or "—") or "—"
    if dim in row and not isinstance(row[dim], (dict, list)):
        return str(row[dim] if row[dim] is not None else "—")
    return str((row.get("labels") or {}).get(dim, "—"))


COLUMNS = [("cost_usd", "usd", "{:>10.4f}"), ("input_tokens", "input", "{:>10,.0f}"),
           ("output_tokens", "output", "{:>10,.0f}"),
           ("cache_read_tokens", "cache rd", "{:>11,.0f}"),
           ("cache_creation_tokens", "cache cr", "{:>11,.0f}"),
           ("total_tokens", "total tok", "{:>12,.0f}"), ("execution_ms", "secs", "{:>8.1f}")]


def pick_provider(rows: list[dict]) -> tuple[str | None, str]:
    """Choose ONE provider when several measured the same thing.

    `otel` and `resultjson` both report cost for the same run - one as it happened, one as
    the tool declared it at the end. Summing them double-counts, and a doubled headline
    figure is worse than no figure, so the default reports a single provider and says which.
    Preference goes to the one carrying the most dimensions, because that is the one that
    can still answer the next question.
    """
    by = defaultdict(set)
    for r in rows:
        if r.get("provider"):
            by[r["provider"]] |= {k for k in r if k in {c[0] for c in COLUMNS}}
    if len(by) < 2:
        return (next(iter(by), None), "")
    overlap = any(by[x] & by[y] for x in by for y in by if x != y)
    if not overlap:
        return (None, "")
    dims = {"otel": 3, "resultjson": 1}       # fallback ordering; richest wins
    best = max(by, key=lambda n: (dims.get(n, 0), len(by[n])))
    others = ", ".join(sorted(n for n in by if n != best))
    return (best, f"{others} also measured these metrics; showing {best} only "
                  f"(--provider <name> to switch, --provider all to sum them).")


def matches(row: dict, wheres: list[str]) -> bool:
    """Every --where must hold. A value list is an OR, so one flag can name a set.

        --where owner=test                  just that agent
        --where owner=test,developer        that set of agents
        --where project=EZFieldhouse        one repo
    """
    for w in wheres or []:
        if "=" not in w:
            raise SystemExit(f"--where needs key=value, got: {w}")
        key, values = w.split("=", 1)
        if dim_of(row, key.strip()) not in {v.strip() for v in values.split(",")}:
            return False
    return True


def cmd_report(a: argparse.Namespace) -> int:
    rows = [r for r in read_rows(a.ledger)
            if (not a.since or str(r.get("ts", "")) >= a.since)
            and matches(r, getattr(a, "where", None))]
    note = ""
    if a.provider and a.provider != "all":
        rows = [r for r in rows if r.get("provider") == a.provider]
    elif not a.provider:
        chosen, note = pick_provider(rows)
        if chosen:
            rows = [r for r in rows if r.get("provider") == chosen]
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"no rows in {a.ledger}")
        return 0

    dim = a.by or "project"
    second = "query_source" if dim == "model" else "model"
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(dim_of(r, dim), dim_of(r, second))].append(r)

    print(f"{dim[:18]:<18} {second[:24]:<24}" + "".join(
        f"{h:>{len(fmt.format(0))}}" for _, h, fmt in COLUMNS))
    print("-" * 122)
    totals = defaultdict(float)
    for key in sorted(groups, key=lambda k: -sum(r.get("cost_usd") or 0 for r in groups[k])):
        g = groups[key]
        cells = ""
        for metric, _, fmt in COLUMNS:
            v = sum(r.get(metric) or 0 for r in g)
            if metric == "execution_ms":
                v /= 1000
            totals[metric] += v
            cells += fmt.format(v)
        print(f"{key[0][:18]:<18} {key[1][:24]:<24}{cells}")
    print("-" * 122)
    print(f"{'TOTAL':<18} {'':<24}" + "".join(
        fmt.format(totals[m]) for m, _, fmt in COLUMNS))
    if note:
        print(f"\n[metrics] {note}")
    return 0


def cost_in_window(samples, agent, start, end, orchestrator='lead'):
    """What `agent` spent BETWEEN two moments.

    Samples are INCREMENTS - Claude Code exports delta temporality, so each one is the
    amount spent since the previous export, not a running total. A window's cost is
    therefore the sum of the increments that fall inside it, with no subtraction and no
    opening balance to establish.

    The window is half-open, (start, end]: a sample exactly on a boundary belongs to the
    step that was closing, not the one about to open, so no increment is counted twice
    across adjacent steps.
    """
    # Three ways a sample can belong to an owner, because there are three ways an agent runs:
    #
    #   1. LABEL - the run was wrapped with --owner/--as. Explicit, so it wins. This is the
    #      only signal when every step is its own top-level session, because then EVERY
    #      sample is `query_source: main` with no agent name and the other two cannot tell
    #      one step from the next.
    #   2. agent.name - the step was spawned as a subagent via the Task tool. Claude Code
    #      names those, and only those.
    #   3. query_source == main - the orchestrator's own turns, which carry no name at all.
    #
    # Checked in that order. Dropping (1) is what made a record of separate per-step
    # sessions report nothing at all, which reads as "never measured" rather than
    # "measured, but not attributable".
    def mine(sm):
        labelled = (sm.get("labels") or {}).get("owner")
        if labelled:
            return labelled == agent
        if sm.get("agent") not in (None, "—", "*"):
            return sm.get("agent") == agent
        return agent == orchestrator and sm.get("query_source") == "main"

    inside = [sm for sm in samples
              if mine(sm)
              and (start is None or (sm.get("ts") or "") > start)
              and (end is None or (sm.get("ts") or "") <= end)]
    if not inside:
        return None
    models = sorted({sm.get("model") for sm in inside if sm.get("model")})
    got = {"usd": 0.0, "input": 0, "output": 0, "cacheRead": 0, "cacheCreation": 0,
           "model": models[0] if len(models) == 1 else ("—" if not models else "mixed")}
    for sm in inside:
        if sm.get("metric") == "claude_code.cost.usage":
            got["usd"] += sm.get("value") or 0
        elif sm.get("metric") == "claude_code.token.usage" and sm.get("type") in got:
            got[sm["type"]] += int(sm.get("value") or 0)
    got["usd"] = round(got["usd"], 6)
    got["total"] = got["input"] + got["output"] + got["cacheRead"] + got["cacheCreation"]
    return got


def cmd_task(a: argparse.Namespace) -> int:
    """A task's run record, with what each step spent joined onto it.

    Nothing here knows what the project calls a unit of work. It reads an `Issue:` field and
    a six-column step table; a ticket, a story and a Bolt are the same shape to it.
    """
    record = Path(a.record)
    if record.is_dir():
        found = sorted(f for f in record.glob("*.md") if f.name.lower() != "readme.md")
        if not found:
            raise SystemExit(f"{record} is a directory and holds no .md record")
        record = found[0]
    if not record.is_file():
        raise SystemExit(f"no such record: {record}")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        caps = [c for c in discover(getattr(a, "provider_dir", None))
                if c["name"] == "runrecord"]
        if not caps:
            raise SystemExit("the runrecord provider is not installed")
        _, rows = _call(caps[0], "collect",
                        {"want": None, "labels": {}, "cwd": os.getcwd(),
                         "record": str(record)}, work)
    if not rows:
        raise SystemExit(f"{record}: no rows this provider can read")

    summary = next((r for r in rows if r.get("kind") == "summary"), {})
    steps = [r for r in rows if r.get("kind") == "step"]
    # Scope samples to THIS task. The ledger is shared across every measured run on the
    # machine, so an unfiltered join silently folds unrelated sessions into the total - and
    # a total that quietly includes someone else's work is worse than no total.
    issue = str(summary.get("issue") or "").strip()
    # Which label carries the issue number is the project's vocabulary, not ours. Try the
    # names projects actually use, and take whichever the ledger really carries - so a repo
    # calling it a ticket and one calling it a Bolt both work with no flag.
    keys = ([a.label_key] if a.label_key else
            ["task", "bolt", "ticket", "issue", "story", "card"])
    samples = [r for r in read_rows(a.ledger) if r.get("kind") == "sample"]
    scoped, used = [], None
    for k in keys:
        hit = [r for r in samples if str((r.get("labels") or {}).get(k, "")) == issue]
        if hit:
            scoped, used = hit, k
            break
    if scoped:
        samples = scoped
    elif samples and issue:
        print(f"[metrics] no samples carry {'/'.join(keys)}={issue}; this run was not "
              f"measured under that label, so no cost is shown.")
        samples = []

    print(f"\n{record}")
    print(f"{'#':<3} {'Step':<22} {'Owner':<10} {'Outcome':<13} {'Model':<18} "
          f"{'USD':>7} {'in':>6} {'out':>8} {'cache rd':>10} {'cache cr':>9} "
          f"{'tokens':>10}  At")
    print("-" * 134)
    total, measured, tok = 0.0, 0, {"input": 0, "output": 0, "cacheRead": 0,
                                    "cacheCreation": 0, "total": 0}
    for r in steps:
        g = cost_in_window(samples, r["agent"], r.get("since"), r["at"], a.orchestrator)
        if g:
            total += g["usd"]
            measured += 1
            for k in tok:
                tok[k] += g[k]
        cmd = r.get("step_cmd") or "—"
        cmd = "—" if cmd in ("", "—") else cmd
        mark = "" if r.get("attempt", 1) == 1 else f" (retry {r['attempt']})"
        n = lambda k: f"{g[k]:,}" if g and g[k] else "—"
        print(f"{r['step']:<3} {(cmd + mark)[:22]:<22} {r['agent'][:10]:<10} "
              f"{r['step_outcome'][:13]:<13} {(g['model'] if g else '—')[:18]:<18} "
              f"{(f'{g[chr(117)+chr(115)+chr(100)]:.4f}' if g else '—'):>7} "
              f"{n('input'):>6} {n('output'):>8} {n('cacheRead'):>10} "
              f"{n('cacheCreation'):>9} {n('total'):>10}  {(r.get('at') or '')[11:19]}")

    # A table that does not reconcile to what was measured is a table that lies quietly.
    # Two kinds of spend belong to no step's owner: the orchestrator's own turns while a
    # delegate holds the run, and `auxiliary` work such as titles and compaction. Showing
    # the remainder is what makes the total checkable against the ledger.
    all_cost = sum(sm.get("value") or 0 for sm in samples
                   if sm.get("metric") == "claude_code.cost.usage")
    leftover = round(all_cost - total, 6)
    if measured and abs(leftover) > 5e-5:
        print(f"{'':<3} {'unattributed':<22} {'—':<10} {'—':<13} "
              f"{'orchestrator/auxiliary':<18} {leftover:>7.4f}")
    print("-" * 134)
    grand = all_cost if measured else total
    print(f"{'':<3} {'':<22} {'':<10} {'':<13} {'TOTAL':<18} "
          f"{(f'{grand:.4f}' if measured else '—'):>7} "
          f"{tok['input']:>6,} {tok['output']:>8,} {tok['cacheRead']:>10,} "
          f"{tok['cacheCreation']:>9,} {tok['total']:>10,}")
    print(f"\nstate: {summary.get('outcome','?')} · steps: {summary.get('steps','?')} · "
          f"rework: {summary.get('rework','?')} · "
          f"human interventions: {summary.get('human_interventions','?')}")
    if not measured:
        print("\n[metrics] no cost for any step: this run was not measured. Cost is joined "
              "from telemetry\n          captured while the run happened, and none overlaps "
              "these timestamps.")
    elif measured < len(steps):
        print(f"\n[metrics] {len(steps) - measured} of {len(steps)} steps have no cost - "
              "no telemetry overlaps their window.")
    return 0



# ---------------------------------------------------------------- doctor

def cmd_doctor(a: argparse.Namespace) -> int:
    """Check this machine, and say what to DO about each thing that is wrong.

    Every failure here was hit for real. The point is not to report health - it is to turn a
    silent, hours-later symptom ("cost columns are empty") into a named cause at install time,
    with the remedy attached. A check with no remedy line does not belong in this list.
    """
    findings = []                       # (level, message, remedy or None)

    def ok(msg):    findings.append(("ok", msg, None))
    def warn(m, r): findings.append(("warn", m, r))
    def fail(m, r): findings.append(("FAIL", m, r))

    # 0. Platform - so a report from a teammate says which OS it came from.
    import platform as _plat
    ok(f"platform: {_plat.system()} {_plat.release()} ({os.name}), "
       f"{_plat.machine()}")

    # 1. Interpreter.
    v = sys.version_info
    if v >= MIN_PYTHON:
        ok(f"python {v.major}.{v.minor}.{v.micro} (needs >= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
    else:
        fail(f"python {v.major}.{v.minor} is too old",
             f"install python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ from python.org")

    # 2. Every provider FILE loads - not just the ones that happen to load.
    files = sorted(f for f in PROVIDER_DIR.glob("*.py") if not f.name.startswith("_"))
    loaded = {c["path"] for c in discover()}
    if not files:
        fail("no provider files found", f"the install is incomplete: {PROVIDER_DIR} is empty")
    for f in files:
        if str(f) in loaded:
            ok(f"provider {f.name} loads")
        else:
            err = subprocess.run([sys.executable, str(f), "capabilities"],
                                 capture_output=True, text=True).stderr.strip().splitlines()
            fail(f"provider {f.name} does not load: {err[-1][:90] if err else 'unknown'}",
                 "re-install; a partial copy or an edited file is the usual cause")

    # 3. THE IMPORTANT ONE: a real loopback round-trip through a real receiver.
    #    This is what catches a firewall, an EDR agent, or a WSL/container namespace split -
    #    none of which announce themselves. Without it the symptom is empty cost columns
    #    hours later, with nothing pointing at the cause.
    try:
        from providers import otel as _unused        # noqa: F401
    except Exception:
        pass
    try:
        import urllib.request
        sys.path.insert(0, str(PROVIDER_DIR))
        import importlib.util
        spec = importlib.util.spec_from_file_location("_otel", PROVIDER_DIR / "otel.py")
        otel = importlib.util.module_from_spec(spec)
        sys.modules["_otel"] = otel
        spec.loader.exec_module(otel)
        coll = otel.Collector()
        srv, port = otel.start_receiver(coll)
        try:
            body = json.dumps({"resourceMetrics": [{"scopeMetrics": [{"metrics": [
                {"name": otel.COST_METRIC, "sum": {"aggregationTemporality": 1,
                 "dataPoints": [{"attributes": [], "asDouble": 1.0}]}}]}]}]}).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/metrics", data=body,
                                         headers={"Content-Type": "application/json"})
            # An explicit no-proxy opener: a machine-wide HTTP_PROXY must not be consulted
            # for loopback, and urllib would consult it.
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            opener.open(req, timeout=10).read()
            if coll.rows():
                ok(f"loopback round-trip works (bound 127.0.0.1:{port}, POST received)")
            else:
                fail("loopback POST was accepted but no data arrived",
                     "unexpected; re-run `metrics --self-test` and report the output")
        finally:
            srv.shutdown()
    except OSError as exc:
        fail(f"cannot use loopback HTTP: {exc}",
             "a firewall, endpoint-security agent, or WSL/container namespace split is "
             "blocking 127.0.0.1. Cost/token capture will be empty; `--output-format json` "
             "still yields session totals via the resultjson provider")
    except Exception as exc:                                  # noqa: BLE001
        fail(f"loopback check could not run: {exc.__class__.__name__}: {exc}",
             "re-install and re-run `metrics doctor`")

    # 4. Proxy environment.
    proxies = [k for k in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy",
                           "ALL_PROXY", "all_proxy") if os.environ.get(k)]
    if proxies:
        noproxy = (os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "")
        if "127.0.0.1" in noproxy or "localhost" in noproxy:
            ok(f"proxy set ({', '.join(proxies)}) and loopback is excluded")
        else:
            warn(f"proxy set ({', '.join(proxies)}) with no loopback exclusion",
                 "the tool sets NO_PROXY on the child itself, so this should be harmless - "
                 "but if cost rows come back empty, export "
                 "NO_PROXY=127.0.0.1,localhost and retry")
    else:
        ok("no proxy environment set")

    # 5. An existing collector would take precedence over the embedded receiver.
    conflict = [k for k in ("OTEL_EXPORTER_OTLP_ENDPOINT",
                            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT") if os.environ.get(k)]
    if conflict:
        warn(f"{conflict[0]} is already set",
             "the embedded receiver will NOT start, so there is no per-agent split. "
             "Session totals still come from the result JSON. Unset it to get the split")
    else:
        ok("no external OTLP collector configured")

    # 6. Ledger writability - checked by actually writing.
    ledger = a.ledger
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        probe = ledger.parent / ".doctor-probe"
        probe.write_text("x", encoding="utf-8")
        probe.unlink()
        ok(f"ledger writable: {ledger}")
    except OSError as exc:
        fail(f"ledger not writable: {exc}",
             f"pick a writable path with --ledger <path> or $AGENT_METRICS_LEDGER")

    # 7. git, and therefore repo scoping.
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10)
        if out.returncode == 0 and out.stdout.strip():
            root = Path(out.stdout.strip())
            ok(f"inside a git repository, ledger scoped to {root.name}")
            gi = root / ".gitignore"
            body = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
            if ".agent-metrics" in body:
                ok(".gitignore excludes .agent-metrics/")
            else:
                warn(".gitignore does not exclude .agent-metrics/",
                     f"run: echo '.agent-metrics/' >> {gi}")
        else:
            warn("not inside a git repository",
                 "the ledger falls back to ~/.claude/metrics/ and is NOT per-project")
    except (OSError, subprocess.SubprocessError):
        warn("git not available",
             "the ledger falls back to ~/.claude/metrics/ and is NOT per-project")

    # 8. Is there anything to measure?
    found = shutil.which("claude")
    if found:
        try:
            ver = subprocess.run(resolve_command(["claude", "--version"]),
                                 capture_output=True, text=True, timeout=30)
            if ver.returncode == 0:
                ok(f"claude spawns: {ver.stdout.strip()[:40] or 'version unknown'}")
            else:
                fail(f"claude found at {found} but exited {ver.returncode}",
                     "check the Claude Code install; the tool cannot measure what it "
                     "cannot start")
        except OSError as exc:
            fail(f"claude found at {found} but cannot be spawned: {exc}",
                 "on Windows a .cmd shim must go through cmd.exe - the tool does this, so "
                 "report this as a bug with the full path above")
    else:
        warn("claude not on PATH",
             "the tool measures any command, but cost/token capture needs Claude Code")

    # 9. WSL - a known way for loopback to be split across namespaces.
    try:
        if "microsoft" in Path("/proc/version").read_text(errors="replace").lower():
            warn("running under WSL",
                 "measure and be measured on the SAME side of the WSL boundary. A claude on "
                 "Windows and a metrics in WSL do not share 127.0.0.1")
    except OSError:
        pass

    width = max(len(m) for _, m, _ in findings) + 2
    for level, msg, remedy in findings:
        print(f"  {level:<4}  {msg}")
        if remedy:
            for i, line in enumerate(_wrap(remedy, 74)):
                print(f"        {'->' if i == 0 else '  '} {line}")
    bad = sum(1 for lv, _, _ in findings if lv == "FAIL")
    warns = sum(1 for lv, _, _ in findings if lv == "warn")
    print(f"\n  {len(findings) - bad - warns} ok, {warns} warning(s), {bad} failure(s)")
    return 1 if bad else 0


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def cmd_tail(a: argparse.Namespace) -> int:
    for r in read_rows(a.ledger)[-a.n:]:
        usd = f"${r['cost_usd']:.4f}" if r.get("cost_usd") is not None else "—"
        print(f"{r.get('ts','?')}  {r.get('provider','?'):<11} {usd:>9}  "
              f"agent={r.get('agent','—')} model={str(r.get('model'))[:28]} "
              f"src={r.get('query_source','—')}")
    return 0


def cmd_capabilities(a: argparse.Namespace) -> int:
    provs = discover()
    if a.json:
        print(json.dumps(provs, indent=2))
        return 0
    print(f"{'provider':<14} {'phase':<8} provides")
    for p in provs:
        print(f"{p['name']:<14} {p['phase']:<8} {', '.join(p.get('provides') or [])}")
    every = sorted({m for p in provs for m in p.get("provides") or []})
    print(f"\n{len(every)} metrics from {len(provs)} providers: {', '.join(every)}")
    return 0


# ---------------------------------------------------------------------- self-test

STUB = '''#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="cmd")
sub.add_parser("capabilities")
c = sub.add_parser("collect"); c.add_argument("--request", required=True)
a = p.parse_args()
if a.cmd == "capabilities":
    print(json.dumps({"name": "STUBNAME", "phase": "PHASE", "provides": ["stub_metric"]}))
elif a.cmd == "collect":
    req = json.loads(Path(a.request).read_text(encoding="utf-8"))
    Path(req["out"]).write_text(json.dumps({"rows": [
        {"provider": "STUBNAME", "stub_metric": 1, "when": req.get("when", "-")}]}),
        encoding="utf-8")
sys.exit(0)
'''


def self_test() -> int:
    fails = []

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'}  caller: {name}")
        if not cond:
            fails.append(name)

    # EVERY provider FILE must load, not just every provider that happens to load.
    # `discover()` skips one that cannot answer `capabilities` - correct at run time, where a
    # broken provider should not take the run down, and exactly wrong here: a syntax error
    # made this suite report PASS with the main provider silently absent. So the files on
    # disk are the population, and a file that does not appear in discovery is a failure.
    print("  provider files:")
    files = sorted(f for f in PROVIDER_DIR.glob("*.py") if not f.name.startswith("_"))
    found = {c["path"] for c in discover()}
    check("at least one provider file exists", bool(files))
    for f in files:
        ok = str(f) in found
        check(f"{f.name} loads and answers capabilities", ok)
        if not ok:
            err = subprocess.run([sys.executable, str(f), "capabilities"],
                                 capture_output=True, text=True).stderr.strip().splitlines()
            if err:
                print(f"          {err[-1][:160]}")

    print("  provider self-tests:")
    for cap in discover():
        rc = subprocess.run([sys.executable, cap["path"], "--self-test"]).returncode
        check(f"{cap['name']} self-test passes", rc == 0)

    print("  caller:")
    with tempfile.TemporaryDirectory() as td:
        pdir, ledger = Path(td) / "providers", Path(td) / "l.jsonl"
        pdir.mkdir()
        for name, phase in (("alpha", "query"), ("beta", "around")):
            f = pdir / f"{name}.py"
            f.write_text(STUB.replace("STUBNAME", name).replace("PHASE", phase),
                         encoding="utf-8")
            f.chmod(0o755)
        (pdir / "broken.py").write_text("this is not python at all\n", encoding="utf-8")
        (pdir / "_skipme.py").write_text(
            STUB.replace("STUBNAME", "skip").replace("PHASE", "query"), encoding="utf-8")

        provs = discover(pdir)
        names = {p["name"] for p in provs}
        check("discovers providers by globbing", {"alpha", "beta"} <= names)
        check("a provider that cannot answer is skipped, not fatal", "broken" not in names)
        check("underscore-prefixed files are ignored", "skip" not in names)
        check("phase order puts around before query",
              [p["name"] for p in provs] == ["beta", "alpha"])

        # Platform shims: Claude Code is `claude` on POSIX, `claude.cmd` or `claude.exe`
        # on Windows. Missing one means --as silently does not inject the agent definition.
        for name in ("claude", "claude.exe", "claude.cmd",
                     r"C:\Users\x\claude.cmd", "/usr/local/bin/claude"):
            check(f"recognised as claude: {name}", is_claude([name]))
        for name in ("claudia", "npm", "clauded.sh"):
            check(f"not mistaken for claude: {name}", not is_claude([name]))
        check("resolve_command leaves an unknown command alone",
              resolve_command(["definitely-not-a-real-binary-xyz"])
              == ["definitely-not-a-real-binary-xyz"])
        check("resolve_command resolves a real one to an absolute path",
              Path(resolve_command([sys.executable.split("/")[-1]])[0]).is_absolute()
              or resolve_command(["python3"])[0].startswith("/"))

        check("select narrows to what was asked for",
              {p["name"] for p in select(provs, {"stub_metric"})} == {"alpha", "beta"})
        check("select excludes providers that supply nothing wanted",
              select(provs, {"nothing_supplies_this"}) == [])
        check("want=None takes everything", len(select(provs, None)) == len(provs))

        # A real dispatch with no wrap provider: the command runs, rows land.
        if True:
            a = argparse.Namespace(provider_dir=str(pdir)) if False else argparse.Namespace(command=["--", sys.executable, "-c", "print('hi')"],
                                   want="stub_metric", all=False, label=["task=901"],
                                   ledger=ledger, provider_dir=str(pdir))
            code = cmd_run(a)
            rows = read_rows(ledger)
            check("exit code passes through with no wrap provider", code == 0)
            check("rows written for each selected provider", len(rows) >= 3)
            check("around provider called twice, before and after",
                  sorted(r.get("when") for r in rows if r.get("provider") == "beta")
                  == ["after", "before"])
            check("labels attached to every row", all(r["labels"] == {"task": "901"} for r in rows))
            check("run id shared across providers", len({r["run"] for r in rows}) == 1)

            # NEGATIVE: a failing child still records, and still returns its own code.
            a.command = ["--", sys.executable, "-c", "import sys; sys.exit(7)"]
            check("failing child keeps its exit code", cmd_run(a) == 7)

            # NEGATIVE: two wrap providers must refuse rather than pick one.
            for n in ("w1", "w2"):
                f = pdir / f"{n}.py"
                f.write_text(STUB.replace("STUBNAME", n).replace("PHASE", "wrap"))
                f.chmod(0o755)
            a.command = ["--", sys.executable, "-c", "pass"]
            try:
                cmd_run(a)
                check("two wrap providers refused", False)
            except SystemExit:
                check("two wrap providers refused", True)

    print(f"\n{'PASS' if not fails else 'FAIL: ' + ', '.join(fails)}")
    return 1 if fails else 0


def main() -> int:
    p = argparse.ArgumentParser(
        prog="metrics", formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Measure what an AI coding agent run cost: tokens, dollars and time, "
                    "broken down per agent and per model.",
        epilog=EXAMPLES)
    p.add_argument("--ledger", type=Path, default=default_ledger(),
                   help="default: <repo root>/.agent-metrics/ledger.jsonl inside a git "
                        "repository, else ~/.claude/metrics/ledger.jsonl")
    p.add_argument("--self-test", action="store_true",
                   help="verify this install, including every provider's own tests")
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("capabilities", help="what is available, and from where")
    c.add_argument("--json", action="store_true")

    r = sub.add_parser(
        "run", help="measure a command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Everything after `--` is measured. Everything before it only describes "
                    "how to file the result,\nso a flag on its own never produces a "
                    "measurement.",
        epilog="examples:\n"
               "  metrics run -- claude -p \"explain this repo\"\n"
               "  metrics run --as test -- claude -p \"/write-tests\"\n"
               "  metrics run --owner ci --label ticket=PROJ-412 -- npm test\n"
               "  metrics run --record .tasks/TASK-42/record.md --owner dev -- claude -p \"...\"\n")
    r.add_argument("--want", help="narrow to these canonical metrics (default: all of them)")
    r.add_argument("--all", action="store_true", help="the default; kept so it can be said")
    r.add_argument("--record", help="a run record: labels by its Issue, and reports after")
    r.add_argument("--owner", help="label the run as this owner, and report as it")
    r.add_argument("--as", dest="as_agent", metavar="AGENT",
                   help="resolve .claude/agents/<AGENT>.md, run as it, and label by it")
    r.add_argument("--label", action="append", default=[], metavar="k=v",
                   help="tag the run; repeatable. Never interpreted - slice by it later")
    r.add_argument("--provider-dir", help="use a different provider set")
    r.add_argument("command", nargs=argparse.REMAINDER)

    rep = sub.add_parser(
        "report", help="read the ledger back",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="--by groups, --where filters. They are independent and compose.\n"
                    "With no --since this covers the ENTIRE ledger, not today.",
        epilog="examples:\n"
               "  metrics report --by owner\n"
               "  metrics report --by query_source        # orchestrator vs subagent\n"
               "  metrics report --where owner=test,dev   # comma is OR\n"
               "  metrics report --where project=x --where owner=test   # repeated is AND\n"
               "  metrics report --json | jq 'del(.[].cmd)'\n")
    rep.add_argument("--by", help="agent, model, query_source, project, or any label")
    rep.add_argument("--provider", help="one provider's rows, or 'all' to sum them")
    rep.add_argument("--where", action="append", default=[], metavar="k=v[,v2]",
                     help="keep only matching rows; repeatable, values are an OR")
    rep.add_argument("--since", help="YYYY-MM-DD")
    rep.add_argument("--json", action="store_true")

    b = sub.add_parser(
        "task", help="a run record, with each step's cost joined on",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Reads an `Issue:` field and a six-column step table. Whatever the "
                    "project calls a unit\nof work - a ticket, a story, a Bolt - is the same "
                    "shape to this.")
    b.add_argument("record")
    b.add_argument("--provider-dir")
    b.add_argument("--label-key", dest="label_key", default=None,
                   help="the label carrying the issue number "
                        "(default: try task, bolt, ticket, issue, story, card)")
    b.add_argument("--orchestrator", default="lead",
                   help="the owner that drives the run; its spend is query_source=main")

    sub.add_parser("doctor", help="check this machine and say how to fix what is wrong")

    t = sub.add_parser("tail", help="the most recent rows, to confirm capture is working",
                       description="Each line is one telemetry export, so a single measured "
                                   "command produces many. Use `report` for totals.")
    t.add_argument("-n", type=int, default=10, help="how many rows (default 10)")

    a = p.parse_args()
    if a.self_test:
        return self_test()
    return {"capabilities": cmd_capabilities, "run": cmd_run, "task": cmd_task,
            "report": cmd_report, "tail": cmd_tail, "doctor": cmd_doctor}.get(
        a.cmd, lambda _a: (p.print_help() or 2))(a)


if __name__ == "__main__":
    sys.exit(main())
