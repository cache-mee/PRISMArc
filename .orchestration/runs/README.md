# Runs

Durable execution state, one directory per unit of work:

```
.orchestration/runs/<WORK-ID>/
  status.json     machine-readable state — schema: ../schemas/status.json
  handoff.md      current handoff — schema: ../schemas/handoff.md
  evidence/       evidence records and captured output — schema: ../schemas/evidence.md
  decisions/      decisions and their rationale
  artifacts/      diffs, reports, logs, superseded handoffs
```

Purpose: execution state and evidence must survive the loss of conversation
context. A fresh agent reading `status.json` and `handoff.md` must know exactly
where things stand.

Rules:

- Created by an agent when real work begins. **No runs exist yet, and none should
  be fabricated.**
- Updated at agent transitions, at gate stops, and at failures.
- Kept small and machine-readable. This is not a workflow database, queue or
  event log, and no runtime should be built around it.
- Conversation transcripts are not state.
- Where state and a claim disagree, state wins.
