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

*An AI-agent-orchestrated SDLC built on Claude Code, Atlassian & GitHub*

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

## What is PRISM?

PRISM is a framework that embeds **purpose-built AI agents** directly into your SDLC. Instead of using AI as a chat assistant, PRISM assigns each role in your team — BA, PM, Architect, UX Designer, Developer, QA, Reviewer — a dedicated agent that knows its job, follows your coding rules, connects to your tools, and hands off cleanly to the next agent. Two more agents work outside the fixed workflow pipeline: **Lead** coordinates complex, multi-agent work on demand, and **Security** runs independent, OWASP-aligned audits standalone or alongside Reviewer.

The result: a team where AI handles the mechanical work of each role, while **humans stay in control through explicit approval gates at every phase boundary**.

> **PRISM is not autonomous.** Every workflow stops at gates and waits for your decision before proceeding.

---

## System Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                        PRISM FRAMEWORK                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   ◈ LAYER 1 — WORKFLOW SKILLS  (own phase sequencing; the pipelines you invoke) ║
║   ┌─────────────────┐  ┌─────────────────────────────────────┐   ║
║   │ sdlc-planning   │  │         DEVELOPMENT SIDE            │   ║
║   │ ─────────────── │  │  sdlc-dev  →  unit-test  →  qa      │   ║
║   │ Idea → Jira     │  │  workflow     workflow     workflow  │   ║
║   └─────────────────┘  └─────────────────────────────────────┘   ║
║                                                                  ║
║   ◈ LAYER 2 — AGENTS  (the role players)                         ║
║   ┌──────────┐ ┌──────┐ ┌──────────┐ ┌──────┐ ┌──────────┐      ║
║   │Business  │ │Prod. │ │Architect │ │  UX  │ │Developer │      ║
║   │Analyst   │ │Mgr   │ │          │ │Design│ │          │      ║
║   └──────────┘ └──────┘ └──────────┘ └──────┘ └──────────┘      ║
║   ┌──────────┐ ┌──────────┐                                      ║
║   │  Test    │ │ Reviewer │                                      ║
║   └──────────┘ └──────────┘                                      ║
║   ┌──────────┐ ┌──────────┐   ↑ fixed workflow phases             ║
║   │   Lead   │ │ Security │   ↓ invoked ad hoc, any time           ║
║   └──────────┘ └──────────┘                                      ║
║                                                                  ║
║   ◈ LAYER 3 — CAPABILITY SKILLS  (bounded capabilities each agent uses) ║
║   bmad-product-brief · bmad-prd · bmad-architecture · bmad-ux    ║
║   bmad-create-epics-and-stories · bmad-build · test-design       ║
║                                                                  ║
║   ◈ LAYER 4 — INTEGRATIONS                                       ║
║   ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐    ║
║   │ Jira (issues) │  │Confluence(docs)│  │  GitHub (code)   │    ║
║   │ via Rovo MCP  │  │ via Rovo MCP   │  │  via gh CLI+git  │    ║
║   └───────────────┘  └────────────────┘  └──────────────────┘    ║
║                                                                  ║
║   ◈ LAYER 5 — STATUS MEMORY                                      ║
║   current.md (7 lines) · status.md (full) · PROJECT-STATUS.md   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## The Three Core Concepts

| Concept | What it means |
|---|---|
| **Agents = Role Players** | Each agent knows its domain and nothing else. The BA doesn't write code. The Developer doesn't design UX. Each agent reads the previous one's output as its input. Seven agents (BA, PM, Architect, UX Designer, Developer, Test, Reviewer) sit on the fixed workflow pipelines; Lead and Security are invoked ad hoc, outside any one phase. |
| **Skills = Two Kinds** | **Capability skills** are a single, reusable capability an agent invokes for one job — writing a brief, designing tests, implementing a task — and never decide what runs next. **Workflow skills** (Layer 1: `sdlc-*-workflow`) are the one named exception — each owns the fixed phase sequence of its own SDLC workflow and invokes the applicable agent per phase. |
| **Gates = Human Control Points** | Every workflow stops at a gate and waits for your explicit reply before proceeding. Gates are never optional. This is how humans stay in control. |

---

## The Agentic Engineering Toolbelt

Agents don't just generate instructions — they operate against the repository
through a layer of deterministic, reusable engineering tools (`tools/`):

```
┌─────────────────────────────┐
│      WORKFLOW SKILL         │   sdlc-*-workflow — owns phase sequencing
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│           AGENT              │   Reason • Decide • Review
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│      CAPABILITY SKILL        │   Reusable procedural knowledge
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│            TOOL              │   Deterministic repo actions
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│       Evidence / State       │
└─────────────────────────────┘
```

Tools provide reliable, observable execution and evidence; agents provide the
reasoning and orchestration on top of them.

### Featured Capabilities

**Scope Check** — mechanically enforces the backend/frontend boundary from this README's Repository Layout, so a change that crosses `B2B_BE/` and `B2B_FE/` fails deterministically instead of relying on an agent to remember the rule. Wired into local pre-commit and CI, and runnable on demand.
`tools/scope-check/scope-check --staged`

**Worktree Add** — creates an isolated, idempotent git worktree (with standard symlinks) for a ticket's branch, so parallel ticket work never collides in one checkout. Cross-platform, with automatic fallbacks on Windows.
`tools/worktree-add/worktree-add feature/PROJ-42-user-login`

**Env Check** — lets an agent confirm a credential is configured without ever being able to print its value, closing the "expand-to-value" leak a naive shell check would cause. It's the safe alternative the secret-leak guard hook points to.
`tools/env-check/env-check <VAR_NAME>`

**Agent Metrics** — measures what an agent run actually cost and did (tokens, cost, rework, human interventions, build status) across independent providers behind one caller, appended to a durable ledger. Its `runrecord` provider is read directly by the `sdlc-*-workflow` skills' Run Record steps, turning workflow evidence into queryable data.
`tools/agent-metrics/metrics report --by agent`

**Security Audit** — read-only, OWASP-aligned dependency/secret/config checks, normalized into structured findings and a PASS/WARN/BLOCK gate verdict (`.claude/skills/security-audit/`, backing the `security` agent).

### Tool Capability Table

| Capability | Tool(s) | What the Agent Gains |
|---|---|---|
| Enforce backend/frontend boundary | `tools/scope-check` | A deterministic PASS/FAIL on whether a diff crosses the repository-layout split |
| Isolate ticket work | `tools/worktree-add` | A ready, idempotent git worktree so parallel tickets never collide |
| Check secrets safely | `tools/env-check` | Confirms a credential is set without ever risking printing its value |
| Measure agent runs | `tools/agent-metrics` | Cost, token, rework and build-status evidence per run, feeding workflow Run Records |
| OWASP-aligned security gate | `.claude/skills/security-audit` | A structured, evidence-backed PASS/WARN/BLOCK security verdict |

### Example: Tools Composed Inside `sdlc-dev-workflow`

```
sdlc-dev-workflow (Workflow Skill)
  │
  ├── worktree-add          → isolated branch + worktree for the ticket
  ├── Developer agent        → implements the plan, commits per task
  ├── scope-check            → validates the diff stays within one folder
  ├── agent-metrics/runrecord → durable evidence row (cost, exit code) in the Run Record
  └── Reviewer agent (new session) → reads plan + PR diff, returns PASS/FAIL
          │
          ▼
     Verifiable Result
```

### Why the Tool Layer Matters

LLMs are good at reasoning, but reliable software execution needs deterministic
mechanisms. Where a check has a clear right answer — does this diff cross a
folder boundary, is this credential configured, what did this run actually
cost — a tool answers it by exit code and evidence, not by an agent's claim.

**Agents reason. Skills provide capabilities. Tools execute deterministically.**
That separation is what lets this system do more than generate text: it can
operate against the repository, validate its own changes, record evidence, and
enforce engineering constraints — and new deterministic capabilities can be
added under `tools/` without changing the underlying Workflow Skill → Agent →
Capability Skill → Tool architecture. See `tools/README.md` for the placement
rule new tools must satisfy.

---

## The Five Workflows

```
╔═══════════════════════════════════════════════════════════════════╗
║                    COMPLETE SDLC PIPELINE                        ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║  /sdlc-planning-workflow                                          ║
║  ─────────────────────────────────────────────────────────────   ║
║  [IDEA] → Brief → PRD → Tech Stack → UX Design → Epics           ║
║         ↓ GATE   ↓ GATE   ↓ GATE      ↓ GATE                     ║
║                    → Confluence Push → Jira Push                  ║
║                                            │                      ║
║                                     [TICKETS IN JIRA]             ║
║                                            │                      ║
║  /sdlc-dev-workflow  ←─────────────────────┘                      ║
║  ─────────────────────────────────────────────────────────────   ║
║  [TICKET] → In Development → Branch → Impl. Plan → Code → PR     ║
║                               ↓ GATE (In Dev)   (commit gates)    ║
║                                           → Code Review           ║
║                                                 │                 ║
║  /sdlc-unit-test-workflow  ←────────────────────┘                 ║
║  ─────────────────────────────────────────────────────────────   ║
║  [BRANCH] → Recon → Test Plan → Write Tests → Commit/Push        ║
║                      ↓ GATE                                       ║
║                                                 │                 ║
║  /sdlc-qa-workflow  ←───────────────────────────┘                 ║
║  ─────────────────────────────────────────────────────────────   ║
║  [PR] → Feature Understanding → Integration Plan → Run Tests     ║
║                                   ↓ GATE         → Jira verdict   ║
║                                                 │                 ║
║                               [PASS → MERGE] / [FAIL → FIX]      ║
║                                                                   ║
║  /workflow-status  (any time, no side effects)                    ║
║  ─────────────────────────────────────────────────────────────   ║
║  Shows project overview or per-ticket "you are here" summary      ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## Quick Reference

| Command | Who | When |
|---|---|---|
| `/sdlc-planning-workflow` | BA / PM | Starting a new feature or initiative |
| `/sdlc-dev-workflow PROJ-42` | Developer | Starting work on a Jira ticket |
| `/sdlc-dev-workflow review PROJ-42` | Developer *(new session)* | After PR is raised |
| `/sdlc-unit-test-workflow PROJ-42` | Developer | After code review passes |
| `/sdlc-qa-workflow PROJ-42` | QA Engineer | After unit tests are pushed |
| `/workflow-status` | Anyone | Project-wide overview |
| `/workflow-status PROJ-42` | Anyone | Per-ticket "you are here" |

---

## Setup Guide

> Full setup guide with troubleshooting: [docs/prism/PRISM-Setup-Guide.md](docs/prism/PRISM-Setup-Guide.md)

### Step 1 — Install Claude Code

Install from [claude.ai/code](https://claude.ai/code) — choose the **VS Code extension** or the **desktop app**.
Sign in with your Anthropic account and open this repository folder.

---

### Step 2 — Connect Atlassian Rovo MCP

This gives Claude Code live access to your Jira and Confluence workspace.

1. In Claude Code, type `/mcp`
2. Select **claude.ai Atlassian Rovo**
3. Click **Needs Auth** — a browser tab opens
4. Sign in with your Atlassian account and authorise
5. Return to Claude Code → click **Check connection**

**Verify:** Ask Claude Code *"List the Jira projects I have access to"* — it should return your project list.

---

### Step 3 — Configure your Atlassian workspace

**`.jira-config.toml`** (repo root):
```toml
[jira_config]
project_key = "SALON"
board_url   = "https://your-org.atlassian.net/jira/software/projects/SALON/boards"
```

**`.confluence-config.toml`** (repo root):
```toml
[confluence_config]
space_key      = "SA"
parent_page_id = ""        # optional: nest all docs under a page
```

---

### Step 4 — Developer / QA additional setup

```bash
# 1. Install Git
winget install --id Git.Git

# 2. Set your Git identity
git config --global user.name "Your Name"
git config --global user.email "you@company.com"

# 3. Install GitHub CLI
winget install --id GitHub.cli --accept-source-agreements --accept-package-agreements

# 4. Authenticate GitHub CLI (run in terminal, not Claude Code)
gh auth login

# 5. Verify repo access
git ls-remote origin
```

---

### Step 5 — BMAD config (first run only)

Create `_bmad/bmm/config.yaml` if it doesn't exist:
```yaml
user_name: "Your Name"
project_name: "salon-app"
communication_language: "English"
planning_artifacts: "bmad-output/planning-artifacts"
```

---

### Step 6 — Agent-cost telemetry (automatic, local-only)

This repo's `.claude/settings.json` enables Claude Code's OpenTelemetry export
(`CLAUDE_CODE_ENABLE_TELEMETRY=1`, pointed at `http://127.0.0.1:4318`) for every session
opened in this project, and a `SessionStart` hook auto-launches a small local collector
(`tools/agent-metrics/otel-persistent-collector.py`) the first time it's needed. No setup
required — it starts itself.

What this means for you:
- Cost/token data for your sessions in this repo (including per-agent breakdown — Developer,
  Reviewer, Test, etc.) is logged to `~/.claude/metrics/otel-sessions.jsonl` **on your own
  machine only**. Nothing is sent anywhere else.
- Read it back any time: `python tools/agent-metrics/otel-persistent-collector.py report --by agent`
- This is separate from `tools/agent-metrics/` itself (the `metrics run`/`report` tool), which
  covers commands you explicitly wrap — see `tools/agent-metrics/README.md`.
- To opt out, delete the `env` block and the `SessionStart` hook from `.claude/settings.json`,
  or add an override in your own `.claude/settings.local.json`.

---

## Role Setup at a Glance

| Role | Additional setup | Primary commands |
|---|---|---|
| **Business Analyst** | None beyond Steps 1–3 | `/sdlc-planning-workflow` |
| **Product Manager** | None beyond Steps 1–3 | `/sdlc-planning-workflow` |
| **Architect** | None beyond Steps 1–3 | `/sdlc-planning-workflow` |
| **UX Designer** | None beyond Steps 1–3 | `/sdlc-planning-workflow` |
| **Developer** | Steps 1–5 (Git + GitHub CLI) | `/sdlc-dev-workflow`, `/sdlc-unit-test-workflow` |
| **QA Engineer** | Steps 1–5 (Git + GitHub CLI) | `/sdlc-qa-workflow` |

---

## Status Memory

PRISM maintains three files to track workflow state efficiently:

| File | Size | Purpose |
|---|---|---|
| `.orchestration/runs/{TICKET}/current.md` | ~7 lines | "You are here" pointer — read on every activation |
| `.orchestration/runs/{TICKET}/status.md` | ~50 lines | Full ticket lifecycle detail — on demand |
| `.orchestration/PROJECT-STATUS.md` | Variable | All tickets, all phases — viewed via `/workflow-status` |

---

## Design Principles

| Principle | What it means in practice |
|---|---|
| **Evidence, not claims** | "Tests passed" is not enough — workflows capture the command, exit code, and output |
| **Human gates** | No phase transition happens without your explicit reply |
| **Bounded recovery** | Each phase gets one retry on failure, then escalates to you |
| **Lean memory** | `current.md` (7 lines) on every activation; full context only on demand |
| **Scope discipline** | Agents implement exactly what the plan says — no extra refactors, no scope creep |
| **Commit granularity** | One commit per task, with your approval on the message |

---

## Repository Layout

```
salon-app/
├── .claude/
│   ├── agents/              — Role agents (BA, PM, Architect, UX, Developer, Reviewer, QA)
│   │                           + Lead (ad-hoc coordination), Security (OWASP audits)
│   ├── skills/              — Workflow skills (sdlc-*-workflow, own phase sequencing)
│   │                           + capability skills (bmad-*, code-review, ...)
│   └── STANDARDS.md         — Normative operating rules (MUST / MUST NOT)
├── .orchestration/
│   ├── policy/              — Gates, retry limits, circuit breakers
│   ├── runs/{TICKET}/       — Per-ticket durable state
│   └── PROJECT-STATUS.md    — Project-wide lifecycle dashboard
├── stack/
│   ├── stack-proposal.md    — Approved tech stack
│   └── rules/
│       ├── base-rules.md    — Coding rules locked by Architect
│       └── client-rules.md  — Project overrides (yours to edit)
├── bmad-output/
│   └── planning-artifacts/  — Brief, PRD, UX specs, Epics (auto-generated)
├── docs/
│   ├── prism/
│   │   ├── PRISM-Overview.md    — Full system overview with walkthrough
│   │   └── PRISM-Setup-Guide.md — Step-by-step setup per role
│   └── adr/                 — Architecture Decision Records
├── .jira-config.toml        — Jira project + board config
├── .confluence-config.toml  — Confluence space config
└── CLAUDE.md                — Operating rules for Claude Code in this repo
```

---

## Further Reading

| Document | What's in it |
|---|---|
| [docs/prism/PRISM-Overview.md](docs/prism/PRISM-Overview.md) | Full system overview with an end-to-end walkthrough example |
| [docs/prism/PRISM-Setup-Guide.md](docs/prism/PRISM-Setup-Guide.md) | Complete setup guide per role + troubleshooting |
| [stack/stack-proposal.md](stack/stack-proposal.md) | Approved tech stack (Flutter + Node.js/TypeScript) |
| [stack/rules/base-rules.md](stack/rules/base-rules.md) | Coding rules — all agents must follow these |
| [.claude/STANDARDS.md](.claude/STANDARDS.md) | Normative AI-development operating rules |
| [tools/README.md](tools/README.md) | The shared deterministic tool layer — what belongs there and why |
| [docs/adr/ADR-0001-agent-owned-orchestration.md](docs/adr/ADR-0001-agent-owned-orchestration.md) | Why this model was chosen |

---

<div align="center">

*Built with [Claude Code](https://claude.ai/code) · Powered by PRISM*

</div>
