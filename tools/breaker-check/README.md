# breaker-check

Evaluates `.orchestration/policy/breakers.json` and `retry-limits.json` against
one run's `.orchestration/runs/<WORK-ID>/status.json` and `handoff.md`. Makes
those two policy files real: today both state, in their own `purpose` /
`enforcement` fields, that nothing enforces them at runtime
(`"enforcement": "convention_only"`). This tool is that check — a
deterministic pass/fail over durable state, never over an agent's own claim
that a breaker didn't trip.

## Args

| Form | Behaviour |
|------|-----------|
| `breaker-check --run-dir <path>` | Evaluate the given run (required) |
| `breaker-check --run-dir <path> --repo-root <path>` | Use this repo root instead of resolving one via `git rev-parse --show-toplevel` from cwd |
| `breaker-check --run-dir <path> --ticket <id>` | Also evaluate the `budget-exceeded` check for this ticket, if `.orchestration/policy/budget-limits.json` exists |
| `breaker-check --help` | Show help |

## Running it, on any OS

Same launcher pattern as `tools/scope-check` and `tools/env-check`:

| Platform | Launcher |
|---|---|
| Linux / macOS | `tools/breaker-check/breaker-check [args]` |
| Windows | `tools\breaker-check\breaker-check.cmd [args]` |

## Exits

| Code | Meaning |
|------|---------|
| 0 | PASS — no breaker tripped, including the legitimate case where `status.json` does not exist yet (many runs — single-agent, no recovery — never produce one) |
| 1 | FAIL — one or more breakers tripped |
| 2 | Usage/error — `status.json` exists but is not valid JSON, or `retry-limits.json` / `breakers.json` under `--repo-root` are missing or malformed. These two policy files are required to exist in this repo; their absence is a real error, not a skip. |

## What it checks

Each check prints one `<id>: ok` or `<id>: TRIPPED — <detail> -> <action>`
line (action taken from the applicable policy entry). A run is `PASS` only if
every check that applies is `ok`.

- **attempt-limit** — groups `status.attempts[]` by `activity`; trips if a
  group's count reaches `retry-limits.json`'s `limits[activity].max_attempts`
  (falling back to `defaults.max_attempts`).
- **no-progress** — within each activity group (sorted by `n`), trips if the
  last two attempts share an identical `failure_signal`.
- **evidence-conflict** — trips if a path in `status.evidence_index[]` does
  not exist, checked relative to the run dir first, then the repo root.
- **gate-encountered** — trips (exit 1) if `status.gate` is non-null. Phrased
  as expected, correct behaviour ("work correctly stopped at gate ...), not a
  defect — but still fails the check so a caller does not proceed past a human
  gate.
- **handoff-insufficient** — if `handoff.md` exists, trips if it is missing
  any of the sections `.orchestration/schemas/handoff.md` requires (Work ID,
  Objective, Acceptance Criteria, Current State, Completed, Failed/Unresolved,
  Constraints, Decisions, Evidence, Next Action, Completion Condition,
  Escalation). If `handoff.md` does not exist at all, this check is skipped
  entirely (no line printed) — its absence is not itself a violation.
- **budget-exceeded** — only evaluated when `.orchestration/policy/budget-limits.json`
  exists *and* `--ticket` was given. Shells out to
  `tools/agent-metrics/metrics.py report --where ticket=<ticket> --json`
  (10s timeout) and sums `cost_usd` across the returned rows. Any failure of
  that call (tool missing, non-zero exit, timeout, unparseable output) is
  printed as `budget-exceeded: SKIP (agent-metrics unavailable: ...)` and does
  **not** count as a trip — this check degrades to a no-op rather than a false
  failure when metrics tooling isn't available.

## What it does not do

- **Does not compare an agent's claim against evidence content.** The
  `evidence-conflict` check only proves an evidence *path* named in
  `evidence_index[]` exists on disk. It cannot and does not judge whether the
  file at that path actually supports the claim made about it — that
  semantic judgement remains a Reviewer/human call
  (`.claude/agents/reviewer.md`).
- **Does not evaluate `scope-expansion`.** `tools/scope-check/` already
  mechanically enforces the one scope rule this repo has (backend/frontend
  folder separation); a general "outside declared scope" check would need
  the handoff's declared scope in a structured, comparable form, which
  `handoff.md` does not currently provide.
- **Is not a sandboxed, always-on enforcement mechanism.** It is invoked by an
  agent (or CI) at a defined checkpoint, the same way `scope-check` is. It
  proves nothing about runs nobody chose to check.

## Intended callers

`.claude/agents/lead.md` and the `sdlc-*-workflow` skills are expected to call
this at bounded-recovery checkpoints — after a Developer/Test/Reviewer attempt,
before deciding whether to retry, escalate, or hand off — the same way
`scope-check` is called before a change is declared finished. That wiring is a
separate, parallel workstream; this tool only needs a `--run-dir` (and
optionally `--repo-root` / `--ticket`) to be called correctly.

## Smoke test

```sh
# No status.json yet → PASS, nothing to evaluate
mkdir -p /tmp/run-empty
tools/breaker-check/breaker-check --run-dir /tmp/run-empty --repo-root .

# A run with a gate set → FAIL, phrased as expected behaviour
mkdir -p /tmp/run-gated
cat > /tmp/run-gated/status.json <<'EOF'
{
  "work_id": "SALON-1", "status": "awaiting_human", "current_agent": null,
  "current_state": "stopped at gate", "attempts": [], "next_action": "await human",
  "gate": {"id": "merge", "question": "Approve merging this PR?"}, "updated_at": "2026-01-01T00:00:00Z"
}
EOF
tools/breaker-check/breaker-check --run-dir /tmp/run-gated --repo-root .
```

## Source

@author Samson Paul, samson.paul@experionglobal.com
