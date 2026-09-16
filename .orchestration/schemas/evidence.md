# Evidence Schema

Evidence proves what actually happened. It is **not** an agent's textual claim.

| | |
|---|---|
| **Claim** | "Tests passed." — an assertion, unverified |
| **Evidence** | command, scope, exit code, result, artifact, timestamp — reproducible |

Records live in `.orchestration/runs/<WORK-ID>/evidence/`, one file per record
(`<evidence-id>.md`), with captured output stored alongside.

---

## Required fields

| Field | Required | Meaning |
|---|---|---|
| `evidence_id` | yes | Unique within the run, e.g. `EV-004` |
| `work_id` | yes | The run this belongs to |
| `agent` | yes | Which agent produced it |
| `type` | yes | `deterministic` or `judgement` |
| `action` | yes | What was being established |
| `command` | for deterministic | The exact command executed |
| `scope` | yes | What was covered — and explicitly what was not |
| `exit_code` | for deterministic | As observed, not inferred from output text |
| `result` | yes | Observed outcome (e.g. "12 passed, 1 failed") |
| `artifact` | yes | Path to captured output or diff |
| `timestamp` | yes | When it ran |
| `interpretation` | yes | What this does and does not prove |

---

## Template

```markdown
# EV-004

- work_id: SALON-123
- agent: developer
- type: deterministic
- action: Verify booking-conflict fix against the failing test
- command: <the project's real test command, as run>
- scope: <test path / package>; did not run the full suite
- exit_code: 0
- result: 12 passed, 0 failed
- artifact: evidence/EV-004.log
- timestamp: 2026-09-03T21:14:07Z
- interpretation: Criterion 2 is satisfied for this test path only.
  Says nothing about the rest of the suite.
```

---

## Rules

- An agent MUST NOT mark work PASS solely because it believes it passed.
- An agent MUST NOT record evidence for a command it did not run.
- `exit_code` MUST be the observed status. Inferring success from output text is
  not evidence.
- `scope` MUST be stated. "All tests pass" without scope is a claim.
- A check that could not run is recorded as **not validated** — never as PASS.
- Non-deterministic conclusions (review opinions, requirement interpretation)
  MUST use `type: judgement`, carry their reasoning, and MUST NOT be presented as
  deterministic evidence.
- `interpretation` MUST state the limits of what the record proves.

## Claim vs evidence conflict

When an agent's claim conflicts with an evidence record — or cites evidence that
does not exist — the `evidence-conflict` breaker in
`.orchestration/policy/breakers.json` applies: **evidence wins, and the workflow
stops.** The conflict itself MUST be recorded, not quietly resolved.

## Known weakness

An agent that writes its own evidence can fabricate it. Today the mitigations are
conventional: records must quote a real command and exit code, and the Reviewer
independently re-runs the decisive check. Whether that holds under real use is an
open question this infrastructure exists to test.
