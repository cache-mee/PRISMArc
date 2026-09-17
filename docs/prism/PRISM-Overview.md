# PRISM — AI-Native SDLC Orchestration Framework

> **PRISM** · **P**lanning · **R**eview · **I**mplementation · **S**tatus · **M**anagement
>
> An AI-agent-orchestrated software development lifecycle built on Claude Code,
> Atlassian (Jira + Confluence), and GitHub — where every role has a dedicated AI
> agent, every phase has a human approval gate, and every decision leaves evidence.

---

## Executive Summary

PRISM is a framework that embeds AI agents directly into your team's SDLC. Instead of using AI as a chat assistant, PRISM assigns each role in your team (BA, PM, Architect, UX Designer, Developer, QA, Reviewer) a purpose-built AI agent that knows its job, follows your coding rules, connects to your tools, and hands off cleanly to the next agent.

The result: a team where AI handles the mechanical work of each role — writing briefs, PRDs, architecture proposals, UX specs, epics, code, tests, and reviews — while humans stay in control through explicit approval gates at every phase boundary.

**What PRISM is not:** an autonomous system that runs without you. Every workflow stops at gates and waits for your decision before proceeding.

---

## System Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                        PRISM FRAMEWORK                           ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   LAYER 1 — WORKFLOW SKILLS  (own phase sequencing; the pipelines you invoke) ║
║   ┌─────────────────┐  ┌─────────────────────────────────────┐   ║
║   │ sdlc-planning   │  │         DEVELOPMENT SIDE            │   ║
║   │ ─────────────── │  │  sdlc-dev  →  unit-test  →  qa      │   ║
║   │ Idea → Jira     │  │  workflow     workflow     workflow  │   ║
║   └─────────────────┘  └─────────────────────────────────────┘   ║
║                                                                  ║
║   LAYER 2 — AGENTS  (the role players, invoked per phase)        ║
║   ┌──────────┐ ┌──────┐ ┌──────────┐ ┌──────┐ ┌──────────┐      ║
║   │Business  │ │Prod. │ │Architect │ │  UX  │ │Developer │      ║
║   │Analyst   │ │Mgr   │ │          │ │Design│ │          │      ║
║   └──────────┘ └──────┘ └──────────┘ └──────┘ └──────────┘      ║
║   ┌──────────┐ ┌──────────┐                                      ║
║   │  Test    │ │ Reviewer │                                      ║
║   └──────────┘ └──────────┘                                      ║
║                                                                  ║
║   LAYER 3 — CAPABILITY SKILLS  (bounded capabilities each agent uses) ║
║   bmad-product-brief · bmad-prd · bmad-architecture · bmad-ux    ║
║   bmad-create-epics-and-stories · bmad-build · test-design       ║
║                                                                  ║
║   LAYER 4 — INTEGRATIONS                                         ║
║   ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐    ║
║   │ Jira (issues) │  │Confluence(docs)│  │  GitHub (code)   │    ║
║   │ via Rovo MCP  │  │ via Rovo MCP   │  │  via gh CLI+git  │    ║
║   └───────────────┘  └────────────────┘  └──────────────────┘    ║
║                                                                  ║
║   LAYER 5 — STATUS MEMORY                                        ║
║   current.md (7 lines) · status.md (full) · PROJECT-STATUS.md   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## The Three Core Concepts

### 1. Agents = Role Players
Each agent knows its domain and nothing else. The Business Analyst doesn't write code. The Developer doesn't design UX. Each agent reads the output of the previous one as its input.

### 2. Skills = Two Kinds
**Capability skills** are a single, reusable capability an agent invokes for one job — writing a brief, designing tests, implementing a task — and never decide what runs next. **Workflow skills** (Layer 1: `sdlc-*-workflow`) are the one named exception — each owns the fixed phase sequence of its own SDLC workflow and invokes the applicable agent per phase.

### 3. Gates = Human Control Points
Every workflow stops at a gate and waits for your explicit reply before proceeding. Gates are never optional. This is how humans stay in control of an AI-powered pipeline.

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
║  [TICKET] → In Progress → Branch → Impl. Plan → Code → PR        ║
║                                     ↓ GATE      (commit gates)    ║
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

## Status Memory — Where Are We?

PRISM maintains three files to track state efficiently:

| File | Size | Purpose | Read by |
|---|---|---|---|
| `current.md` | ~7 lines | "You are here" pointer | Every workflow on activation |
| `status.md` | ~50 lines | Full ticket lifecycle detail | On demand (`detail` reply) |
| `PROJECT-STATUS.md` | Variable | All tickets, all phases | `/workflow-status` only |

```
/workflow-status           → project overview
/workflow-status PROJ-42   → ticket drill-down
```

---

## End-to-End Walkthrough: "Add Service Categories to Salon App"

This example follows a single feature from idea to QA pass.

### Step 1 — Planning (BA, PM, Architect, UX, BA)

The product owner has an idea: *"Salons should be able to group their services into categories like Hair, Nails, Skin."*

```
> /sdlc-planning-workflow

PRISM: Hello! I'll walk you through the planning pipeline.
       Phases: Brief → PRD → Tech Stack → UX → Epics → Confluence → Jira
       What is the idea or MVP you want to plan?

You:   Salons should be able to group their services into categories.
       Customers should be able to filter by category when browsing.
```

**Phase 1 — Business Analyst writes the brief**
- BA agent asks clarifying questions (personas, scope, risks)
- Produces `brief.md` + `addendum.md`

```
── GATE 1: BRIEF REVIEW ──────────────────────────────────────
Brief ready at: bmad-output/planning-artifacts/briefs/brief-salon-app-2026-09-04/brief.md

Reply: approved / revise: <notes> / stop
```

```
You: approved
```

**Phase 2 — Product Manager writes the PRD**
- PM reads the brief, asks questions to resolve assumptions
- Produces `prd.md` with functional requirements per persona (Customer, Salon Partner)

**Phase 3 — Architect proposes the tech stack**
- Architect reads the PRD, proposes stack
- On approval: locks `stack/rules/base-rules.md`

**Phase 4 — UX Designer produces screen specs**
- Derives screens from the PRD: Category Management (Salon Partner), Category Filter (Customer)
- Produces one file per flow

**Phase 5 → 7 — Epics, Confluence, Jira**
- BA creates epics + stories from PRD + UX
- All docs pushed to Confluence space
- Epics + stories pushed to Jira

Result in Jira:
```
Epic: Service Category Management    SALON-10
  Story: Create a service category   SALON-11
  Story: Edit a service category     SALON-12
  Story: Delete a service category   SALON-13

Epic: Customer Category Browsing     SALON-14
  Story: Filter services by category SALON-15
```

---

### Step 2 — Development (Developer)

Developer picks up `SALON-11`:

```
> /sdlc-dev-workflow SALON-11

PRISM: New ticket. Running GitHub pre-flight...
       ✓ Remote: cache-mee/salon-app
       ✓ Identity: abhijat.krishna
       ✓ Clean working tree

Reading SALON-11 from Jira...
  Summary: Create a service category
  Acceptance criteria:
    - Salon partner can create a category with a name and optional description
    - Category name must be unique per salon
    - Returns 201 with the created category on success

Ticket transitioned → In Progress ✓
Branch created: feature/SALON-11-create-service-category ✓
Pushed to origin ✓
```

**Phase 3 — Implementation Plan**

Developer agent reads the ticket + coding rules, produces:
```
Task 1: Add Category model         (Low)
Task 2: Add POST /categories API   (Medium)
Task 3: Add CategoryService layer  (Medium)
```

```
── GATE 3: IMPLEMENTATION PLAN REVIEW ────────────────────────
Plan ready. 3 tasks. Approve to begin coding.
Reply: approved / revise: <notes> / stop
```

```
You: approved
```

**Phase 4 — Code, commit by commit**

```
── COMMIT: Add Category model ────────────────────────────────
Files staged: src/models/category.ts

Suggested: SALON-11: Add Category model
           Adds Category schema with name, description, salonId fields.

Reply: use / edit: <your message> / skip
```

```
You: use
```

After all 3 tasks:

```
── PUSH CONFIRMATION ─────────────────────────────────────────
Commits to push:
  a1b2c3d SALON-11: Add Category model
  d4e5f6g SALON-11: Add POST /categories endpoint
  h7i8j9k SALON-11: Add CategoryService with uniqueness validation

Reply: push / no
```

```
You: push
```

PR created → Jira transitioned to "In Review".

---

### Step 3 — Code Review (Reviewer, new session)

```
> /sdlc-dev-workflow review SALON-11

Reviewer reads: ticket + implementation plan + PR diff
Produces: .orchestration/runs/SALON-11/review.md

── REVIEW RESULT ─────────────────────────────────────────────
MAJOR: src/services/category.ts:42 — uniqueness check runs after insert,
       not before. Race condition possible under concurrent requests.
MINOR: src/models/category.ts:8 — magic number 255 should be MAX_NAME_LENGTH constant.

Verdict: FAIL — address MAJOR before merge.
```

Developer fixes → pushes → re-runs review → PASS.

---

### Step 4 — Unit Tests (Developer)

```
> /sdlc-unit-test-workflow SALON-11

Phase 1: Reads CategoryService, CategoryController, Category model
Phase 2: Designs test plan (happy path, duplicate name, empty name, long name)

── GATE 2: UNIT TEST PLAN REVIEW ────────────────────────────
8 test cases across 3 units. Approve to write tests.
Reply: approved / revise / stop
```

Tests written, all pass, committed and pushed.

---

### Step 5 — QA (QA Engineer)

```
> /sdlc-qa-workflow SALON-11

Phase 1: Reads ticket + PR diff
Phase 2: Designs integration test plan
         AC1: POST /categories creates and persists a category → 2 test cases
         AC2: Duplicate name returns 409 → 1 test case

── GATE 2: INTEGRATION TEST PLAN REVIEW ─────────────────────
3 integration test cases. Approve to write tests.
Reply: approved / revise / stop
```

Tests run against real DB → all pass.

```
── QA VERDICT: PASS ──────────────────────────────────────────
3/3 integration tests passed.
Jira → Ready for Merge ✓
PR comment added ✓
```

**SALON-11 is ready to merge.**

---

## Quick Reference

| Command | Who | When |
|---|---|---|
| `/sdlc-planning-workflow` | BA / PM | Starting a new feature or initiative |
| `/sdlc-dev-workflow PROJ-N` | Developer | Starting work on a Jira ticket |
| `/sdlc-dev-workflow review PROJ-N` | Developer (new session) | After PR is raised |
| `/sdlc-unit-test-workflow PROJ-N` | Developer | After code review passes |
| `/sdlc-qa-workflow PROJ-N` | QA Engineer | After unit tests are pushed |
| `/workflow-status` | Anyone | Project-wide overview |
| `/workflow-status PROJ-N` | Anyone | Per-ticket "you are here" |

---

## Design Principles

| Principle | What it means in practice |
|---|---|
| **Evidence, not claims** | "Tests passed" is not enough — the workflow captures the command, exit code, and output |
| **Human gates** | No phase transition happens without your explicit reply |
| **Bounded recovery** | Each phase gets one retry on failure, then escalates to you |
| **Lean memory** | `current.md` (7 lines) on every activation; full context only on demand |
| **Scope discipline** | Agents implement exactly what the plan says — no extra refactors, no scope creep |
| **Commit granularity** | One commit per task, with your approval on the message |
