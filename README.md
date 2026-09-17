<div align="center">

<br/>

```
██████╗ ██████╗ ██╗███████╗███╗   ███╗
██╔══██╗██╔══██╗██║██╔════╝████╗ ████║
██████╔╝██████╔╝██║███████╗██╔████╔██║
██╔═══╝ ██╔══██╗██║╚════██║██║╚██╔╝██║
██║     ██║  ██║██║███████║██║ ╚═╝ ██║
╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝     ╚═╝
```

### **P**lanning · **R**eview · **I**mplementation · **S**tatus · **M**anagement

*An agent-orchestrated SDLC, running on a deterministic execution harness*

<br/>

![Planning](https://img.shields.io/badge/Planning-AI%20Powered-6366f1?style=for-the-badge&logo=claude&logoColor=white)
![Review](https://img.shields.io/badge/Review-Automated-ec4899?style=for-the-badge&logo=github&logoColor=white)
![Implementation](https://img.shields.io/badge/Implementation-Agent%20Driven-f59e0b?style=for-the-badge&logo=flutter&logoColor=white)
![Status](https://img.shields.io/badge/Status-Live%20Tracked-10b981?style=for-the-badge&logo=jira&logoColor=white)
![Management](https://img.shields.io/badge/Management-Human%20Gated-3b82f6?style=for-the-badge&logo=confluence&logoColor=white)

<br/>

[![Claude Code](https://img.shields.io/badge/Requires-Claude%20Code-orange?style=flat-square)](https://claude.ai/code)
[![Atlassian Rovo](https://img.shields.io/badge/Integrates-Atlassian%20Rovo%20MCP-0052CC?style=flat-square&logo=atlassian)](https://www.atlassian.com/rovo)
[![GitHub CLI](https://img.shields.io/badge/Uses-GitHub%20CLI-181717?style=flat-square&logo=github)](https://cli.github.com)
[![Stack](https://img.shields.io/badge/Stack-Flutter%20%2B%20Node.js-02569B?style=flat-square&logo=flutter)](stack/stack-proposal.md)

</div>

---

## 1. What We Built

PRISM is two things, layered together:

1. An **agent-orchestrated SDLC** — BA, PM, Architect, UX Designer, Developer,
   Test and Reviewer sit on fixed workflow pipelines; Lead and Security are
   invoked ad hoc. Each agent knows its domain and hands off cleanly to the
   next.
2. Underneath it, a **deterministic execution harness** — Claude Code hooks
   and standalone tools that constrain what those agents can actually do to
   the repository, independent of whether the agent remembers to behave.

The harness isn't a separate product bolted on for show: it's
`.claude/hooks/`, `tools/`, and `.orchestration/policy/`, wired directly into
every workflow skill and agent contract in this repo.

## 2. Why This Is Different

Most agent setups stop at "the agent was told not to." Being told is not a
control — it's a hope. This repo adds a layer that doesn't depend on the
agent choosing to comply:

| | |
|---|---|
| **LLM decides** | what to attempt, given the ticket and the plan |
| **Harness controls** | whether that attempt is even allowed to reach a tool call |
| **Deterministic tools enforce** | exit-code checks with no judgement involved — scope, gates, budgets |
| **Verification proves** | an independent re-run, not the acting agent's own claim |
| **Telemetry measures** | tokens, cost, duration — and feeds a real budget check, not only a dashboard |

Concretely: `.orchestration/policy/gates.json` has always *said* a human must
approve a merge. Until `.claude/hooks/gate-guard.py` existed, nothing checked
that — an agent could run `gh pr merge` and nothing would stop it. The same
was true of retry limits, cost ceilings, and write-time scope. All four are
now mechanically enforced; see the table below.

## 3. AI Execution Harness

```
AGENT (LLM)
  │  decides what to attempt
  ▼
HARNESS / CONTROL PLANE        Claude Code PreToolUse hooks + workflow skills
  │  establishes scope, checks policy, checks budget
  ▼
POLICY · SCOPE · BUDGET · SECURITY    gates.json · breakers.json · budget-limits.json
  │  evaluated by tools — never by agent self-report
  ▼
DETERMINISTIC TOOLS    scope-check · policy-guard · gate-guard · breaker-check · env-check
  │  exit 0 / 1
  ▼
CHANGES                files, commits, PRs
  │
  ▼
VERIFICATION           Reviewer / Test agents re-run the decisive check independently
  │
  ▼
EVIDENCE · STATE · TELEMETRY    run-record.md · status.json · OTel + agent-metrics
  │
  ▼
NEXT AGENT DECISION
```

| Capability | Mechanism | Benefit |
|---|---|---|
| Scope enforcement | `tools/scope-check` (pre-commit + CI) **and** `tools/policy-guard` (`Write`/`Edit` `PreToolUse` hook) | A cross-boundary change is blocked the moment it's written, not just when someone later commits |
| Human-approval gating | `.claude/hooks/gate-guard.py` (`PreToolUse`, fail-closed) against `.orchestration/policy/gates.json` | `gh pr merge`, `git push origin main`, force-push, release and dependency-add commands are blocked before they execute |
| Execution/retry control | `tools/breaker-check` against `breakers.json` / `retry-limits.json` | Retry, no-progress, evidence-conflict and handoff-insufficient breakers are checked against durable state before a retry is granted |
| Cost/budget control | `tools/breaker-check --ticket` against `budget-limits.json`, sourced from `tools/agent-metrics` | A ticket's cumulative real cost is checked against a ceiling before more work continues |
| Secret safety | `.claude/hooks/secret-leak-guard.py` (fail-closed) + `tools/env-check` | Blocks a command that would print a raw secret value; lets an agent confirm a credential is set without ever seeing it |
| Agent/ticket isolation | `tools/worktree-add` | Each ticket gets its own git worktree — parallel work can't collide |
| Verification | Reviewer / Test agents, `.claude/skills/verification` | An independent re-run of the decisive check, not the acting agent's assertion |
| Durable state / recovery | `.orchestration/runs/<TICKET>/{current,status,run-record}.md`, `status.json` | A fresh agent or session resumes from disk, not from conversation history |
| Observability | Claude Code OTel export + local collector + `tools/agent-metrics` | Tokens, cost, duration, rework — feeding the budget breaker above, not only a report |
| Security scanning | `.claude/skills/security-audit` (OWASP-aligned) | Structured PASS/WARN/BLOCK verdict backing the Security agent |

## 4. Security

- **Fail-closed where it matters.** `secret-leak-guard.py` and `gate-guard.py`
  block on their *own* internal errors rather than silently letting a command
  through — the opposite of this repo's general fail-open hook default,
  deliberately, because these two exist to stop something irreversible.
- **Gates are mechanical, not advisory.** `gates.json` names merge,
  push-to-shared-branch, destructive-operation, release and dependency-change
  as requiring human approval; `gate-guard.py` blocks the Bash commands that
  would trigger them, with no agent-side override.
- **Scope is enforced twice** — at write time (`policy-guard`, live) and at
  commit time (`scope-check`, pre-commit + CI) — defense in depth, not a
  single point of failure.
- **Secrets are never exposed to check them.** `env-check` reports
  `SET`/`EMPTY`/`UNSET` only, never the value.
- **Independent security audit.** `.claude/skills/security-audit` runs
  read-only, OWASP-aligned dependency/secret/config checks on demand,
  producing a PASS/WARN/BLOCK gate verdict.

## 5. Token & Cost Efficiency

- `current.md` (~7 lines) is the only state read on every agent activation;
  `status.md` and `PROJECT-STATUS.md` are read on demand, not by default.
- Claude Code's own OpenTelemetry export, plus a local persistent collector
  (`tools/agent-metrics/otel-persistent-collector.py`), capture tokens, cost
  and duration per session and per agent — on your machine only.
- That telemetry isn't just a report: `tools/breaker-check --ticket` checks a
  ticket's cumulative real cost against `budget-limits.json`'s ceiling before
  its work continues.

## 6. Verification & Evidence

- **Claim vs. evidence.** An agent's "tests passed" is not accepted as proof;
  a command, its exit code, and its output are.
- **Independent re-run.** The Reviewer and Test agents re-run the decisive
  check themselves rather than trusting the Developer's report.
- **Durable evidence.** `run-record.md` carries a per-task evidence row
  (command, exit code) for every ticket. `status.json`'s `attempts[]` — written
  only by `breaker-check record-attempt`, never hand-edited — is what
  `breaker-check` evaluates breakers against, so a malformed hand-edit can't
  silently break the check.

## 7. Isolation & Recovery

- **Ticket isolation.** `tools/worktree-add` gives every ticket branch its own
  git worktree (with standard symlinks), so parallel tickets can't collide in
  one checkout.
- **Bounded recovery.** Each phase gets one retry on failure; `tools/breaker-check`
  checks that against real attempt history before granting it, and stops and
  escalates on exhaustion or a repeated failure signal — not on an agent's
  promise to be careful.
- **Resumable state**, three layers, each read only when needed:

  | File | Size | Purpose |
  |---|---|---|
  | `.orchestration/runs/{TICKET}/current.md` | ~7 lines | "You are here" pointer — read on every activation |
  | `.orchestration/runs/{TICKET}/status.md` | ~50 lines | Full ticket lifecycle detail — on demand |
  | `.orchestration/runs/{TICKET}/status.json` | small, machine-readable | Attempts/gate/breaker state — written by `breaker-check record-attempt`, evaluated by `breaker-check` |

  A fresh agent or session resumes from these files, never from conversation
  history.

## 8. Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                        PRISM FRAMEWORK                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   ◈ LAYER 1 — WORKFLOW SKILLS  (own phase sequencing)            ║
║   ┌─────────────────┐  ┌─────────────────────────────────────┐   ║
║   │ sdlc-planning   │  │         DEVELOPMENT SIDE            │   ║
║   │ Idea → Jira     │  │  sdlc-dev → unit-test → qa workflow  │   ║
║   └─────────────────┘  └─────────────────────────────────────┘   ║
║                                                                  ║
║   ◈ LAYER 2 — AGENTS  (the role players)                         ║
║   BA · PM · Architect · UX · Developer · Test · Reviewer          ║
║   Lead / Security — invoked ad hoc, outside any one phase         ║
║                                                                  ║
║   ◈ LAYER 3 — CAPABILITY SKILLS  (bounded, reusable capabilities) ║
║   bmad-product-brief · bmad-prd · bmad-architecture · bmad-ux    ║
║   bmad-create-epics-and-stories · bmad-build · test-design       ║
║                                                                  ║
║   ◈ LAYER 4 — HARNESS  (see §3 — hooks + tools, always on)       ║
║   gate-guard · policy-guard · breaker-check · scope-check · ...  ║
║                                                                  ║
║   ◈ LAYER 5 — INTEGRATIONS                                       ║
║   Jira / Confluence (Rovo MCP) · GitHub (gh CLI + git)            ║
╚══════════════════════════════════════════════════════════════════╝
```

| Concept | What it means |
|---|---|
| **Agents = Role Players** | Each agent knows its domain and nothing else; each reads the previous one's output as its input. |
| **Skills = Two Kinds** | **Capability skills** do one job and never decide what runs next. **Workflow skills** (`sdlc-*-workflow`) own their phase sequence and invoke the applicable agent per phase — the one named exception. |
| **Gates = Human Control Points** | Every workflow stops at a gate and waits for your explicit reply. Gates are never optional — and, per §3/§4, the consequential ones are now mechanically enforced, not just declared. |

```
╔═══════════════════════════════════════════════════════════════════╗
║                    COMPLETE SDLC PIPELINE                        ║
╠═══════════════════════════════════════════════════════════════════╣
║  /sdlc-planning-workflow                                          ║
║  [IDEA] → Brief → PRD → Tech Stack → UX Design → Epics           ║
║         ↓ GATE   ↓ GATE   ↓ GATE      ↓ GATE                     ║
║                    → Confluence Push → Jira Push → [TICKETS]     ║
║                                                                   ║
║  /sdlc-dev-workflow                                               ║
║  [TICKET] → In Development → Branch → Impl. Plan → Code → PR     ║
║                               ↓ GATE (In Dev)   (commit gates)    ║
║                                           → Code Review           ║
║                                                                   ║
║  /sdlc-unit-test-workflow                                         ║
║  [BRANCH] → Recon → Test Plan → Write Tests → Commit/Push        ║
║                      ↓ GATE                                       ║
║                                                                   ║
║  /sdlc-qa-workflow                                                ║
║  [PR] → Feature Understanding → Integration Plan → Run Tests     ║
║                                   ↓ GATE         → Jira verdict   ║
║                               [PASS → MERGE] / [FAIL → FIX]      ║
║                                                                   ║
║  /workflow-status  (any time, no side effects)                    ║
╚═══════════════════════════════════════════════════════════════════╝
```

| Command | Who | When |
|---|---|---|
| `/sdlc-planning-workflow` | BA / PM | Starting a new feature or initiative |
| `/sdlc-dev-workflow PROJ-42` | Developer | Starting work on a Jira ticket |
| `/sdlc-dev-workflow review PROJ-42` | Developer *(new session)* | After PR is raised |
| `/sdlc-unit-test-workflow PROJ-42` | Developer | After code review passes |
| `/sdlc-qa-workflow PROJ-42` | QA Engineer | After unit tests are pushed |
| `/workflow-status [PROJ-42]` | Anyone | Project-wide or per-ticket "you are here" |

## 9. Demo / Proof

Runnable right now, from the repo root, no setup required — these are real
deterministic checks, not agent-reported results:

```bash
# Blocks a merge before it happens (PreToolUse hook, as Claude Code invokes it)
echo '{"tool_name":"Bash","tool_input":{"command":"gh pr merge 42 --squash"}}' \
  | python3 .claude/hooks/gate-guard.py

# Blocks a cross-boundary write before it happens (exit 1)
tools/policy-guard/policy-guard check-scope --files B2B_BE/example.py B2B_FE/example.tsx

# Full harness test suite
python3 -m pytest .claude/hooks/tests/ tools/breaker-check/tests/ -q
tools/policy-guard/policy-guard --self-test
```

## 10. Getting Started

> Full setup guide with troubleshooting: [docs/prism/PRISM-Setup-Guide.md](docs/prism/PRISM-Setup-Guide.md)

**Step 1 — Install Claude Code.** From [claude.ai/code](https://claude.ai/code) (VS Code extension or desktop app). Sign in and open this repo folder.

**Step 2 — Connect Atlassian Rovo MCP.** `/mcp` → **claude.ai Atlassian Rovo** → **Needs Auth** → sign in → **Check connection**. Verify: ask *"List the Jira projects I have access to."*

**Step 3 — Configure your Atlassian workspace** in `.jira-config.toml` / `.confluence-config.toml` (repo root).

**Step 4 — Developer / QA setup** (Git, GitHub CLI):
```bash
winget install --id Git.Git
git config --global user.name "Your Name"
git config --global user.email "you@company.com"
winget install --id GitHub.cli --accept-source-agreements --accept-package-agreements
gh auth login          # run in a terminal, not Claude Code
git ls-remote origin    # verify repo access
```

**Step 5 — BMAD config (first run only).** Create `_bmad/bmm/config.yaml`:
```yaml
user_name: "Your Name"
project_name: "salon-app"
communication_language: "English"
planning_artifacts: "bmad-output/planning-artifacts"
```

**Step 6 — Agent-cost telemetry (automatic, local-only).** `.claude/settings.json` enables OTel export and auto-launches a local collector on `SessionStart` — nothing to configure. Cost/token data lands in `~/.claude/metrics/otel-sessions.jsonl` **on your machine only**; read it with `python tools/agent-metrics/otel-persistent-collector.py report --by agent`. To opt out, remove the `env` block and `SessionStart` hook from `.claude/settings.json`.

### Role Setup at a Glance

| Role | Additional setup | Primary commands |
|---|---|---|
| **Business Analyst / Product Manager / Architect / UX Designer** | None beyond Steps 1–3 | `/sdlc-planning-workflow` |
| **Developer** | Steps 1–5 (Git + GitHub CLI) | `/sdlc-dev-workflow`, `/sdlc-unit-test-workflow` |
| **QA Engineer** | Steps 1–5 (Git + GitHub CLI) | `/sdlc-qa-workflow` |

### Repository Layout

```
salon-app/
├── .claude/
│   ├── agents/              — Role agents (BA, PM, Architect, UX, Developer, Reviewer, QA)
│   │                           + Lead (ad-hoc coordination), Security (OWASP audits)
│   ├── hooks/                — Harness enforcement: gate-guard.py, secret-leak-guard.py
│   ├── skills/               — Workflow skills (sdlc-*-workflow) + capability skills
│   └── STANDARDS.md         — Normative operating rules (MUST / MUST NOT)
├── .orchestration/
│   ├── policy/               — gates.json, breakers.json, retry-limits.json, budget-limits.json
│   ├── runs/{TICKET}/       — Per-ticket durable state (current.md, status.md, status.json, run-record.md)
│   └── PROJECT-STATUS.md    — Project-wide lifecycle dashboard
├── tools/
│   ├── scope-check/          — Backend/frontend boundary, at commit time
│   ├── policy-guard/          — Backend/frontend boundary, at write time
│   ├── gate-guard.py (in .claude/hooks/) — human-gate enforcement
│   ├── breaker-check/        — retry/no-progress/budget breaker evaluation
│   ├── worktree-add/, env-check/, agent-metrics/
│   └── README.md             — placement rule for new tools
├── stack/                     — Approved tech stack + coding rules
├── bmad-output/               — Generated planning artifacts (brief, PRD, UX, epics)
├── docs/{prism,adr}/          — Overview, setup guide, ADRs
├── .jira-config.toml, .confluence-config.toml
└── CLAUDE.md                  — Operating rules for Claude Code in this repo
```

### Further Reading

| Document | What's in it |
|---|---|
| [docs/prism/PRISM-Overview.md](docs/prism/PRISM-Overview.md) | Full system overview with an end-to-end walkthrough example |
| [docs/prism/PRISM-Setup-Guide.md](docs/prism/PRISM-Setup-Guide.md) | Complete setup guide per role + troubleshooting |
| [stack/stack-proposal.md](stack/stack-proposal.md) | Approved tech stack (Flutter + Node.js/TypeScript) |
| [stack/rules/base-rules.md](stack/rules/base-rules.md) | Coding rules — all agents must follow these |
| [.claude/STANDARDS.md](.claude/STANDARDS.md) | Normative AI-development operating rules |
| [.claude/hooks/README.md](.claude/hooks/README.md) | Harness hooks — what's enforced and how, fail-open vs. fail-closed |
| [tools/README.md](tools/README.md) | The shared deterministic tool layer — what belongs there and why |
| [docs/adr/ADR-0001-agent-owned-orchestration.md](docs/adr/ADR-0001-agent-owned-orchestration.md) | Why this model was chosen |

---

<div align="center">

*Built with [Claude Code](https://claude.ai/code) · Powered by PRISM*

</div>
