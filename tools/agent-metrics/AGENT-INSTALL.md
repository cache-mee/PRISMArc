# agent-metrics — installation and integration, for an AI agent

**You are an AI coding agent. This file is addressed to you, not to the user.** Follow it to
install `agent-metrics` into the user's project and to answer their questions about using it.
The user should not have to run anything themselves, install a dependency, edit a config file,
or read this document.

Measures what an AI coding agent run cost: tokens (input, output, cache read, cache creation),
dollars, wall-clock time — **broken down per agent and per model** — plus rework, human
interventions and outcome when a run record exists.


---

## READ THIS BEFORE YOU DO ANYTHING — five rules that override your defaults

You are installing a tool whose whole purpose is to produce trustworthy numbers. Your normal
instinct to be helpful — to fix what looks broken, to summarise, to tidy up — destroys that.
These five rules are not style preferences; breaking any one of them has already produced a
false "installation complete" in testing.

**1. NEVER modify any file that came out of the archive.**
Not to fix a syntax error, not to patch an import, not to regenerate a corrupted file, not to
"improve" anything. If a file does not load, that is the finding — **report it and stop**. A
silently repaired install is not the tool that was shipped, it is a different tool nobody
reviewed, and the person who sent you the archive now believes their copy is good when it is
not. This has happened: an agent given a deliberately corrupted provider repaired it, reported
"all provider modules load correctly", and the sabotage went unnoticed.

**2. NEVER commit, stage, or push anything.**
Not the tool, not the `.gitignore` edit, not a "chore: install tooling" commit. The person
asked you to install something, not to change their history. Leave the working tree dirty and
say what you changed.

**3. Report `doctor`'s output VERBATIM. Do not summarise it, and never restate a check as
passing unless you saw that exact line.**
Paste the block. A tick-list you composed from memory is how a failure becomes a success in
the retelling.

**4. Extract ONCE, into `tools/`, and clean up after yourself.**
Do not leave a stray copy at the repository root, do not leave the `.zip` behind, and add
`__pycache__/` to `.gitignore` alongside `.agent-metrics/` if it appears. The repository
should contain exactly `tools/agent-metrics/` and nothing else new.

**5. If `doctor` reports a FAIL, the install has not succeeded.**
Say so plainly. Do not proceed to the smoke test, do not describe the tool's features, and do
not end with a summary that reads like success. The correct output in that case is the
`doctor` block, the `->` remedy line it printed, and one sentence saying the install is
blocked.

### When this is a first run on Windows or macOS

The tool has only been executed on Linux. If `platform:` in `doctor`'s first line says
anything else, **you are the verification**, and your job is to produce a report someone can
forward — not to make the install succeed.

End your reply with exactly this block and nothing added to it:

```
PLATFORM REPORT
<paste doctor's full output, all lines>
<paste the last line of --self-test>
<paste the report --by owner table, or the error if there was one>
```

Then say, in one sentence, whether every check passed. If any did not, name it and quote the
`->` remedy. Do not attempt the remedy unless it is the `.gitignore` line.

---

## 0. Decide the install location BEFORE copying anything

Ask yourself one question: **is the user measuring one project, or all their work?**

| | Install to | Ledger lands at |
|---|---|---|
| One project (**default — prefer this**) | `<repo>/tools/agent-metrics/` | `<repo>/.agent-metrics/ledger.jsonl` |
| Everything on the machine | `~/.claude/tools/agent-metrics/` | same repo-scoped path when inside a repo |

The ledger is resolved at run time, not at install time: inside a git repository it is always
`<repo root>/.agent-metrics/ledger.jsonl`, so **a per-project install and a machine-wide
install produce identically scoped data.** The choice is only about who else gets the tool.

Default to the per-project install. Choose machine-wide only if the user says they want it
across several repos.

---

## 1. Check the prerequisite (one command)

```bash
python3 --version || python --version || py -3 --version
```

Python **3.8+** is the only requirement. The tool imports stdlib exclusively — `argparse`,
`collections`, `datetime`, `gzip`, `http`, `json`, `os`, `pathlib`, `re`, `shlex`,
`subprocess`, `sys`, `tempfile`, `threading`, `time`, `uuid`. **Never run `pip install`.**

If no Python 3 exists, stop and tell the user to install it from python.org. Do not attempt
to install Python yourself.

---

## 2. Install

### Per-project (default)

```bash
mkdir -p tools
cp -r /path/to/agent-metrics tools/
chmod +x tools/agent-metrics/metrics.py tools/agent-metrics/providers/*.py
```

Then add ONE line to the repository's `.gitignore`:

```
.agent-metrics/
```

Commit the tool, never the ledger. The tool is reviewable source; the ledger is local
measurement that would conflict on every merge.

### Machine-wide (only if asked)

```bash
mkdir -p ~/.claude/tools
cp -r /path/to/agent-metrics ~/.claude/tools/
chmod +x ~/.claude/tools/agent-metrics/metrics.py ~/.claude/tools/agent-metrics/providers/*.py
mkdir -p ~/.local/bin && cp ~/.claude/tools/agent-metrics/metrics ~/.local/bin/metrics
chmod +x ~/.local/bin/metrics
```

`~/.local/bin` is on PATH on most systems. If it is not, tell the user to add
`export PATH="$HOME/.local/bin:$PATH"` to their shell profile — that is the only thing in this
whole document you may ask a user to do, and only if it is genuinely absent.

On Windows use `metrics.cmd` instead of `metrics`, and skip `chmod`.

---

## 3. Verify — do not report success without this

**Run `doctor` first. It is the check that turns a silent, hours-later symptom into a named
cause with a remedy attached.**

```bash
python3 tools/agent-metrics/metrics.py doctor          # exit 0 = no failures
python3 tools/agent-metrics/metrics.py --self-test     # expect the last line to be: PASS
```

`doctor` checks nine things and prints a `->` remedy line for every one that is not `ok`:
the interpreter version; that every provider FILE loads; **a real loopback round-trip through
a real receiver** (the check that catches a firewall, an endpoint-security agent, or a
WSL/container namespace split - none of which announce themselves); proxy environment;
an already-configured external collector; ledger writability, tested by writing; git and
therefore repo scoping; the `.gitignore` line; and whether `claude` is on PATH.

**Act on what it prints.** A `warn` has a remedy you can usually apply yourself - a missing
`.gitignore` line is the common one. A `FAIL` means the install does not work; fix it and
re-run rather than proceeding.

Exit code is 1 if anything failed, 0 otherwise - so `doctor` is safe to gate on in a script.

A self-test that does not end in `PASS` means a broken install. Report the failure; do not
work around it.

Then a smoke test that costs nothing:

```bash
python3 tools/agent-metrics/metrics.py run --owner smoke -- echo ok
python3 tools/agent-metrics/metrics.py report
```

---

## 3b. Windows and macOS — what is different, and what to check

The tool is stdlib-only Python and runs on all three platforms, but **it has only been
executed on Linux**. Treat the first run on Windows or macOS as verification, not routine.

### macOS

Install and run exactly as on Linux. Two differences:

- `python` may not exist; `python3` does on any machine with the Xcode command line tools.
  The `metrics` launcher probes both, so use the launcher rather than a hardcoded name.
- If the team uses an endpoint-security agent (common on managed Macs), it may intercept
  loopback. `doctor`'s round-trip check is what tells you.

### Windows

- Use **`metrics.cmd`**, not the `metrics` shell script. Skip `chmod` entirely - it does
  nothing there, and the providers are launched via the Python interpreter rather than an
  executable bit.
- `py -3` is tried before `python`. **`python3` is deliberately not tried** - on Windows it
  is usually a Microsoft Store stub that opens the app page instead of running anything.
- Claude Code installs as **`claude.cmd`**, and Windows `CreateProcess` cannot execute a
  `.cmd` at all. The tool resolves the command through `shutil.which` and routes a batch
  shim via `%COMSPEC% /c`; without that, every measured run would die with `WinError 193`
  before starting. If you see that error, report it - it means the resolution failed.
- Paths in the ledger will contain backslashes. That is cosmetic; every comparison the tool
  makes is separator-agnostic.

### The verification to run once per platform

Ask one person on each OS to run these four commands in any git repository and send back the
output. It takes under two minutes and costs a few cents.

```bash
python -m pip --version                      # just to confirm which python is in play
metrics doctor                               # or: python tools/agent-metrics/metrics.py doctor
metrics --self-test
metrics run --owner probe -- claude -p "say ok"
metrics report --by owner
```

What each result means:

| Result | Meaning |
|---|---|
| `doctor` ends `0 failure(s)` | the platform is fine; proceed |
| `loopback round-trip works` | firewall / endpoint-security / namespace are all clear - this is the check that cannot be reasoned about, only run |
| `FAIL cannot use loopback HTTP` | per-agent capture will not work here. Session totals still work via `--output-format json`; report the exact message |
| `FAIL claude found ... but cannot be spawned` | the `.cmd` resolution failed - report the full path it printed |
| `--self-test` ends `PASS` | every provider loads and every guard fires |
| `report` shows a non-zero `usd` | end to end works on this platform |

The first line of `doctor` reports the OS, release and architecture, so a pasted result
identifies itself without anyone having to say which machine it came from.

---

## 4. How to invoke it — the one rule

**Everything after `--` is measured. Everything before `--` describes how to file the result.**

A flag alone never produces a measurement. `metrics run --owner test` fails with
`nothing to measure` because it names an owner but no command.

```bash
metrics run -- <any command>                         # the minimum that works
metrics run --as test -- claude -p "..."             # run as an agent, labelled by it
metrics run --record <run-record> --owner test -- claude -p "..."   # measure AND report
```

---

## 5. Integrating it into the user's project

Pick the pattern that matches how they actually run agents. Do not apply more than one.

### 5a. They invoke agents from the shell or a script

Put `metrics run` in front of the invocation, and add a label naming the unit of work:

```bash
metrics run --as test --label ticket=1234 -- claude -p "/write-tests ..."
```

Nothing else changes: stdout passes through, the exit code is the child's own.

### 5b. They have a task runner (Makefile, npm script, shell function)

Wrap it once, where the invocation already lives, so nobody has to remember:

```make
agent:
	python3 tools/agent-metrics/metrics.py run --as $(AGENT) --label task=$(TASK) -- \
	  claude -p "$(PROMPT)"
```

### 5c. They have an orchestration layer with run records

If the project writes a per-task record with a step table (`| # | Step | Owner | ... | At |`),
pass `--record`. The measurement is labelled by the record's `Issue:` and the per-step table
prints automatically:

```bash
metrics run --record .tasks/TASK-42/TASK-42.md --owner developer -- claude -p "..."
metrics task .tasks/TASK-42/TASK-42.md --orchestrator lead
```

`--orchestrator` names the owner that DRIVES the run. This matters: Claude Code tags only
subagents with `agent.name`; a top-level session reports as `query_source: main` with no name.
If the driving agent was started with `--append-system-prompt` rather than spawned as a
subagent, you must name it or its cost joins to nothing.

### 5d. They want everything measured, including interactive sessions

`metrics run` cannot see a session it did not start — it cannot wrap the session it is
running inside. For that, tell them about the two alternatives and let them choose:

- `npx ccusage@latest daily` — retroactive, reads transcripts already on disk, zero setup,
  but no per-agent split and list-price only.
- Claude Code's own OpenTelemetry export to a collector they run — captures every session
  including interactive, but needs a collector and edits `~/.claude/settings.json`.

Do not set up the OpenTelemetry option without explicit permission: it changes global
configuration and affects every session on the machine.

---

## 6. Reading the data back

```bash
metrics report                                  # grouped by project
metrics report --by owner                       # per agent
metrics report --by model                       # per model
metrics report --by query_source                # main vs subagent vs auxiliary
metrics report --where owner=test               # one agent
metrics report --where owner=test,developer     # a set (comma = OR)
metrics report --where project=x --by owner     # repeatable --where is AND
metrics report --since 2026-09-16               # from a date; there is no --until
metrics report --json | jq 'del(.[].cmd)'       # raw rows; drop cmd, it is huge
metrics tail -n 10                              # recent samples, to confirm capture works
```

`--by` groups, `--where` filters. They are independent and compose.

---

## 6b. Sample commands to hand the user

Copy these verbatim when the user asks "how do I ...". They are grouped by the question
being asked, not by flag. Replace `metrics` with
`python3 tools/agent-metrics/metrics.py` for a per-project install without a launcher.

### "How do I measure an agent run?"

```bash
# the simplest possible measurement
metrics run -- claude -p "explain this repo"

# run as a named agent defined in .claude/agents/, labelled by it
metrics run --as test -- claude -p "/write-tests for the login module"

# tag it with whatever unit of work you use
metrics run --as developer --label ticket=PROJ-412 -- claude -p "/write-code"

# cap the spend (this flag belongs to claude, not to metrics)
metrics run --as test -- claude -p "..." --max-budget-usd 2.00
```

### "What did my last run cost?"

```bash
metrics report                      # everything, grouped by project
metrics tail -n 5                   # the most recent rows
```

### "Which agent is spending the most?"

```bash
metrics report --by owner           # per agent you labelled
metrics report --by agent           # per subagent Claude Code named itself
metrics report --by query_source    # orchestrator vs subagent vs background
```

### "How much did one agent cost?"

```bash
metrics report --where owner=test
metrics report --where owner=test,developer      # a set; comma means OR
```

### "How much did this ticket / feature cost?"

```bash
metrics run --label ticket=PROJ-412 -- claude -p "..."    # label it when you run it
metrics report --where ticket=PROJ-412 --by owner          # then slice by it
```

### "Which model is costing me money?"

```bash
metrics report --by model
metrics report --where owner=test --by model               # one agent, split by model
```

### "What did we spend this week?"

```bash
metrics report --since 2026-09-14
metrics report --since 2026-09-14 --by owner
```

There is no `--until`. With no `--since` the report covers the **entire** ledger, not today.

### "Show me the cost of each step of a task"

```bash
metrics run --record .tasks/TASK-42/TASK-42.md --owner developer -- claude -p "..."
metrics task .tasks/TASK-42/TASK-42.md --orchestrator lead
```

### "Give me the raw numbers / I want to script this"

```bash
metrics report --json | jq 'del(.[].cmd)'                  # cmd is huge; drop it
metrics report --where ticket=PROJ-412 --json | jq '[.[].cost_usd] | add'
metrics capabilities --json
```

### "Is it installed correctly?"

```bash
metrics --self-test         # last line must read: PASS
metrics capabilities        # 14 metrics from 3 providers
```

### "What did this whole project cost, including sessions I never wrapped?"

```bash
npx ccusage@latest daily
npx ccusage@latest session
```

Different tool, reads transcripts already on disk. No per-agent split, but it sees
interactive sessions that `metrics run` cannot.

---

## 7. Facts you will need when the user asks

- **The report has no default time window.** With no `--since` it covers the entire ledger.
  Say so rather than implying it is "today".
- **Cost is list price.** It is the figure the tool itself reported (`costBasis: "list"`).
  On a subscription it is list-equivalent spend, not an invoice. Good for comparison.
- **Cache-read is usually 80-95% of all tokens.** That ratio explains an otherwise surprising
  cost, and it is why cache-read and cache-creation are separate metrics rather than "cached".
- **Two providers measure cost.** `otel` (live, splits by agent) and `resultjson` (the tool's
  own end-of-run figure, whole session). The report picks `otel` and says so; they should
  agree to the cent, and disagreement means an export was lost.
- **An agent that refuses to act writes no row it owns**, so its spend has nowhere to hang in
  the `task` view and lands on the previous step. Prefer `report --where owner=...` when a run
  contains refusals.
- **Per-agent cost and tokens exist; per-agent time and lines-changed do not.** Claude Code
  does not dimension those by agent. Do not invent them.

---

## 8. Troubleshooting — every failure actually hit while building this

Each entry is a real symptom with its real cause. Work down the list; they are ordered by how
often they happen. Where a symptom has several causes, they are listed cheapest-to-check first.

### `metrics.py: command not found` (exit 127)

The launcher is `metrics`, with no `.py`. The file itself is not on PATH and is not executable
by name. Use whichever applies:

```bash
metrics <args>                                   # machine-wide install, launcher on PATH
python3 tools/agent-metrics/metrics.py <args>    # per-project install
```

### `nothing to measure: put the command after --` (exit 1)

No command was given. **`--owner`, `--as`, `--label`, `--record` and `--want` describe how to
file a result; none of them produces one.** There must be a `--` followed by something to run.

```bash
metrics run --owner test                 # WRONG - measures nothing
metrics run --owner test -- npm test     # right
```

### `unrecognized arguments: -as` (exit 2)

Long options take two dashes: `--as`, not `-as`. This fails even when a command is present,
because argparse rejects the flag before looking at anything else. There are no single-letter
short forms except `-n` on `tail`.

### `--want names 'cost', 'tokens', which no provider supplies`

Use the canonical metric names, which `metrics capabilities` lists. `cost_usd`, not `cost`;
`total_tokens`, not `tokens`. Before this check existed, a mistyped `--want` selected no
provider, ran the command, recorded an exit code and measured nothing - silently.

### The report shows `—` for cost, or "no cost for any step"

Five causes, cheapest first:

1. **The run was never wrapped.** `metrics` records only what `metrics run` starts. A `claude`
   invoked directly leaves no trace. Check `metrics tail`.
2. **Wrong ledger.** The default is repo-scoped: `<repo root>/.agent-metrics/ledger.jsonl`
   inside a git repository, `~/.claude/metrics/ledger.jsonl` outside one. Data captured under
   a different default needs `--ledger <path>`.
3. **`--orchestrator` does not name a real owner.** Only subagents get `agent.name`; a
   top-level session reports as `query_source: main` with no name. If the driving agent was
   started with `--append-system-prompt`, name it: `metrics task <record> --orchestrator test`.
4. **The label and the record disagree.** `task` matches ledger rows whose label equals the
   record's `Issue:`. It tries `task`, `bolt`, `ticket`, `issue`, `story`, `card`; if the run
   used a different label name, pass `--label-key <name>`.
5. **The step window does not overlap the spend.** A step's window runs from the PREVIOUS
   row's `At` to its own, so the row must be stamped AFTER the work it covers - which is what
   an agent recording its own outcome does naturally. A record written up-front with
   placeholder timestamps will join to nothing.

### An agent refused to act, and its cost landed on the wrong step

Expected, and not fixable in the `task` view. An agent that stops without writing a row it
owns leaves its spend with nowhere to hang, so it falls into the previous step's window or the
`unattributed` line. **Use `metrics report --where owner=<name>` for runs containing refusals** -
label attribution does not depend on the record having a row.

### The measured command produced no output and no ledger rows

Two causes:

- **The output was piped into something that exits early.** `metrics run ... | head -1` closes
  the pipe, the child takes SIGPIPE and dies before any telemetry is exported. Redirect to a
  file instead.
- **The child was waiting on stdin.** `claude -p` warns `no stdin data received in 3s`. Add
  `< /dev/null`.

### Edits to the tool had no effect

There are two copies: the source you edited and the installed one being run. A zip is a
snapshot. Re-install after every change:

```bash
rm -rf tools/agent-metrics && unzip -q -o agent-metrics.zip -d tools
```

### `claude` consumed the prompt as a flag argument

Variadic flags such as `--allowedTools` swallow what follows. Separate them:

```bash
claude --allowedTools Task -p --model <m> -- "the prompt"
```

### `--owner` is silently wrong

`--owner` takes any string, so a typo is recorded rather than rejected and then matches nothing
at report time - the cost column reads `—` as though the run was never measured. When
`--record` is present the tool warns; otherwise there is nothing to check against. Prefer
`--as <agent>`, which must resolve `.claude/agents/<agent>.md` and therefore cannot be
misspelled silently.

### The totals are too small, or two providers disagree

`otel` and `resultjson` measure the same run by different routes and should agree to the cent.
A real gap means an export was lost. Raise the drain window - `otel.py` accepts `--drain`
(seconds after exit to wait for the final export, default 2.0). Note the caller does not
currently pass it through, so this needs editing the provider.

### Writing a provider: two traps that produce plausible wrong numbers

- **OTLP temporality.** Claude Code exports `aggregationTemporality: 1` (DELTA) - each point is
  an increment and points must be **added**. Treating them as cumulative (taking the newest
  value per attribute set) looks reasonable and silently discards every export but the last.
- **`usage` vs `modelUsage`.** In the result JSON, `usage` is the LAST TURN only while
  `total_cost_usd` is the whole session. On a 28-turn run those differ by ~100x. Read
  `modelUsage`, summed across models.

Both have their own self-test, because neither raises an error when you get it wrong.

### `no Python 3 found` (exit 127)

The launcher tried `python3`, `python`, `py` and `python3.13`-`python3.8`, asking each its
version. None answered 3. Install Python 3.8+ from python.org. On Windows use `metrics.cmd`.

### The ledger got committed to git

The `.gitignore` line was missed. Add `.agent-metrics/` and `git rm -r --cached .agent-metrics`.
Nothing in the tool enforces this - it is step 2 of the install for a reason.

---

## 9. Things you must not do

- Do not `pip install` anything. If you think you need a dependency, you have the wrong tool.
- Do not add a price table. Every number is the one Claude Code reported; a hardcoded table
  goes stale silently and turns a missing number into a wrong one.
- Do not commit `.agent-metrics/`. Add it to `.gitignore` instead.
- Do not edit `~/.claude/settings.json` to enable global telemetry without explicit permission.
- Do not report the install as done without a `PASS` from `--self-test`.
- Do not tell the user to run the install commands. Run them.

---

## 10. Uninstall

```bash
rm -rf tools/agent-metrics          # or ~/.claude/tools/agent-metrics and ~/.local/bin/metrics
```

The ledger at `.agent-metrics/` survives on purpose. Delete it separately if the user wants
the history gone.

---

@author Samson Paul, samson.paul@experionglobal.com
