# Run Record Schema

The durable, **cross-workflow** ledger consumed by `tools/agent-metrics` (the `runrecord`
provider) to report rework, human interventions, outcome and per-step timing for one unit of
work — across every `sdlc-*-workflow` skill that touches it, not just one.

This file is **additive to**, never a replacement for, each workflow's own status artifact
(`status.md`, `current.md`, `workflow-status.md`, `development/plans/*`). It exists only so
`tools/agent-metrics` has one shape to read regardless of which workflow is currently active.

## Where it lives

| Unit of work | Path | Spans |
|---|---|---|
| One ticket | `.orchestration/runs/{ticket}/run-record.md` | `sdlc-dev-workflow` → `sdlc-unit-test-workflow` → `sdlc-qa-workflow` — all three append to the **same file**, because all three already share `{run_dir}` for that ticket |
| One planning cycle | `.orchestration/runs/planning-{project_name}/run-record.md` | all seven phases of `sdlc-planning-workflow`, since planning runs before any ticket exists |

A ticket's record MAY carry a `Task:` field pointing back at the planning-cycle record it came
from, so the full path from idea to shipped ticket is traceable through one chain of files.

## Required shape

`runrecord.py` reads a header field block, then a strict **six-column** table. A row that is
not exactly six cells is silently skipped — never guessed at — so match this exactly:

```markdown
# {WORK-ID} — run record
<!-- Appended by every sdlc-*-workflow phase and gate that touches this work. Do not hand-edit. -->

Issue:  {ticket key, e.g. PROJ-42 — or the project name for a planning-cycle record}
Branch: {branch name, or "n/a" before Phase 2 creates one}
State:  {see State values below}
Next:   {exact next action, one line}
Task:   {optional — path to the planning-cycle run-record.md this ticket originated from}

| # | Step | Owner | Outcome | Evidence | At |
|---|---|---|---|---|---|
| 1 | [workflow-tag] Phase N — Name | agent-or-human | done\|failed\|awaiting | evidence-ref | 2026-09-17T09:02:14+00:00 |
```

## Field rules

- **Issue / Branch / Next** — updated in place; always reflect current reality, not history.
- **State** — one of: `planning` · `in-development` · `unit-testing` · `qa` · `complete` ·
  `stopped`. Whichever workflow is currently active sets it on entry and again on handoff to
  the next workflow. This is what makes the record read as one continuous SDLC journey instead
  of four disconnected logs.
- **# (step number)** — increases across the **whole** record, not reset per workflow. A
  retried step reuses the same number — that is what the `rework` metric counts. A phase
  belonging to a later workflow gets the next free number, continuing the same sequence.
- **Step** — prefixed with the workflow tag in square brackets — `[planning]`, `[dev]`,
  `[unit-test]`, `[qa]` — followed by the phase name exactly as that workflow's own pipeline
  names it (e.g. `[dev] Phase 3 — Implementation Plan`). The tag is what lets one file show
  which workflow produced which row; nothing else in the record says so.
- **Owner** — the acting agent's name (`lead`, `business-analyst`, `product-manager`,
  `architect`, `ux-designer`, `developer`, `test`, `reviewer`), or exactly `human` for a gate
  reply. `runrecord.py` only counts a row as a human intervention when `Owner` is exactly
  `human` — any other spelling silently is not counted.
- **Outcome** — `done`, `failed`, or `awaiting` (a gate not yet answered).
- **Evidence** — a short reference, not a transcript: `commit:<sha>`, `exit:<code>:<command>`,
  `jira:transitioned`, `approved`, `pr:<url>`, or a path. `runrecord.py` reads `exit:<code>:`
  specifically to derive `build_status`.
- **At** — ISO-8601 timestamp, stamped when the row is written — i.e. when the step
  *completes*, not when it starts. A step's cost window is measured from the previous row's
  `At` to its own; stamping early attributes the wrong window to the wrong step.

## When to append a row

Every workflow phase and every gate reply appends exactly **one** row, at the same moment that
workflow already updates its own status artifact. Never rewrite or delete an existing row — a
retry is a new row at the same `#`, not an edit to the old one.

## Reading it back

```bash
metrics task .orchestration/runs/{ticket}/run-record.md --orchestrator lead
metrics report --where owner=developer
metrics report --where ticket={ticket} --by owner
```

## Relationship to other durable state

This schema is narrower than `handoff.md` on purpose: it carries only what `runrecord.py` can
read deterministically (steps, owners, outcomes, timestamps). It does not replace a handoff's
narrative content (acceptance criteria, decisions, constraints) — see `handoff.md` — and it
does not replace `status.json`'s machine state for breakers/gates/retries. It is a fourth,
metrics-shaped view of the same run, kept only because a metrics tool needs one file whose
shape does not change no matter which workflow wrote the latest row.
