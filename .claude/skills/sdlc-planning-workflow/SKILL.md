---
name: sdlc-planning-workflow
description: General-purpose planning-phase SDLC orchestration. Takes an idea or MVP description and drives it through discovery → brief → PRD → tech stack → UX design → epics & stories → Confluence push → Jira push, with human approval gates at each phase. Covers planning only — development and testing are handled by a separate workflow. Invoke this when starting work on any new feature or product initiative.
---

# SDLC Planning Workflow

Orchestration rules: `.claude/STANDARDS.md`. This skill owns the workflow sequence
— it does not implement any phase itself. Each phase belongs to the agent named
for it. Human gates are stops, not suggestions.

## Conventions

- `{project-root}` is the repository root.
- `{planning_artifacts}` resolves to `bmad-output/planning-artifacts`.
- `{stack_root}` resolves to `{project-root}/stack`.
- `{run_id}` resolves to `planning-{project_name}`.
- `{run_record}` resolves to `.orchestration/runs/{run_id}/run-record.md`.
- A **human gate** means: stop, present the artefact, wait for explicit user approval before continuing. Never reinterpret a gate as optional.
- **Evidence, not claims.** Each phase must produce a file on disk before the gate is presented. A claim that an artefact exists is not evidence.
- **Bounded recovery.** Each phase gets one retry on failure before escalating to the user.

---

## Run Record (agent-metrics)

Schema: `.orchestration/schemas/run-record.md`. This record is project-scoped, not
ticket-scoped, since planning runs before any ticket exists.

- On first use, create `{run_record}` with `Issue: {project_name}`, `State: planning`.
- After **every** phase below completes, and after every gate reply (`approved` / `revise` /
  `stop`), append one row: `Step` = `[planning] Phase N — Name` (or `[planning] Gate N —
  Name`), `Owner` = `business-analyst` / `product-manager` / `architect` / `ux-designer` for a
  phase, or exactly `human` for a gate reply, `Outcome` = `done` / `failed` / `awaiting`,
  `Evidence` = the artefact path just produced (or `approved` / `revise` for a gate), `At` =
  now, ISO-8601.
- When Phase 7 (or the last enabled phase) completes, set `State: complete`. On a `stop` reply
  at any gate, set `State: stopped` instead.
- When Phase 7 pushes tickets to Jira, record each created ticket key in that row's `Evidence`
  field (e.g. `created:PROJ-42,PROJ-43`) — this is what lets a later ticket's own run-record
  point back here via its `Task:` field.
- Never let this slow down or gate the workflow itself — it is a durable side-effect, not a
  decision point. If `{run_record}` cannot be written, note it and continue; do not stop the
  workflow over a metrics file.

---

## On Activation

1. Load `{project-root}/_bmad/bmm/config.yaml` for `{user_name}`, `{project_name}`, `{communication_language}`, `{planning_artifacts}`.
2. Greet `{user_name}` in `{communication_language}`. Explain the pipeline briefly (phases + gates) so the user knows what to expect. Be explicit that this workflow covers **planning only** — a separate development and testing workflow follows.
3. Check for an in-progress run: scan `{planning_artifacts}` for a `workflow-status.md` file whose `status` field is not `complete`. If found, offer to resume from the last completed phase rather than starting over.
4. If no resume candidate, begin at **Phase 1**.

---

## The Pipeline

```
[IDEA / MVP INPUT]
        │
        ▼
  Phase 1: Discovery & Brief    (Business Analyst)
        │
  ── GATE 1: Brief Approval ────────────────── user must approve before Phase 2
        │
        ▼
  Phase 2: PRD                  (Product Manager)
        │
  ── GATE 2: PRD Approval ──────────────────── (implicit — reviewed inline)
        │
        ▼
  Phase 3: Tech Stack           (Architect)
        │
  ── GATE 3: Stack Approval ────────────────── user must approve; creates stack/ folder
        │
        ▼
  Phase 4: UX Design            (UX Designer)
        │
  ── GATE 4: Design Approval ───────────────── user must approve before Phase 5
        │
        ▼
  Phase 5: Epics & Stories      (Business Analyst)
        │
        ▼ (automatic)
  Phase 6: Confluence Push      (Rovo MCP — if .confluence-config.toml enabled)
        │
        ▼ (automatic)
  Phase 7: Jira Push            (Rovo MCP — if .jira-config.toml enabled)
        │
        ▼
  [PLANNING COMPLETE — hand off to Development & Testing workflow]
```

---

## Phase 1: Discovery & Brief

**Owner:** Business Analyst agent (`.claude/agents/business-analyst.md`)
**Skill:** `bmad-product-brief`
**Output:** `{planning_artifacts}/briefs/brief-{project_name}-{date}/brief.md` + `addendum.md`

### Instructions

1. Invoke the Business Analyst agent. Pass it the user's idea/MVP input verbatim as the source.
2. The BA agent runs `bmad-product-brief` in **Create** intent:
   - Conducts discovery: surfaces domain, form-factor, personas, stakes, and key risks.
   - Identifies and flags all assumptions as `[ASSUMPTION]`.
   - Produces `brief.md` (distilled, 1–2 pages) and `addendum.md` (persona depth, technical considerations, risks, open questions).
   - Seeds `.memlog.md` via `memlog.py init`.
3. Record the workspace path in `{planning_artifacts}/workflow-status.md` under `phase_1.workspace`.
4. Log completion: `memlog.py append --type event --text "Phase 1 complete: brief produced at <path>"`.

### Gate 1 — Brief Approval

Present the brief to the user:

```
── GATE 1: BRIEF REVIEW ──────────────────────────────────────────────────────
Brief is ready at: {planning_artifacts}/briefs/{run_folder}/brief.md

Please review. When ready, reply with one of:
  approved          → proceed to Phase 2 (PRD)
  revise: <notes>   → BA agent revises the brief then re-presents it
  stop              → end the workflow here
──────────────────────────────────────────────────────────────────────────────
```

Do not proceed until the user replies `approved`. On `revise`, the BA agent applies the notes and re-presents; one revision cycle before escalating to the user for guidance. On `stop`, write final status to `workflow-status.md` and halt.

---

## Phase 2: PRD

**Owner:** Product Manager agent (`.claude/agents/product-manager.md`)
**Skill:** `bmad-prd`
**Input:** Approved brief + addendum from Phase 1
**Output:** `{planning_artifacts}/prd/prd-{project_name}-{date}/prd.md`

### Instructions

1. Invoke the Product Manager agent. Pass it the path to the approved brief and addendum.
2. The PM agent runs `bmad-prd` in **Create** intent:
   - Reads the brief and addendum in full before eliciting.
   - Resolves every `[ASSUMPTION]` tag through clarifying questions with the user — none may survive into the final PRD without a documented resolution.
   - Groups functional requirements by persona (derived from the brief — do not assume a fixed set of personas).
   - Documents out-of-scope items explicitly so the Architect and UX Designer have a clear boundary.
   - Seeds `.memlog.md` for the PRD workspace.
3. Record the PRD path in `workflow-status.md` under `phase_2.prd_path`.
4. Log completion: `memlog.py append --type event --text "Phase 2 complete: PRD produced at <path>"`.

> PRD review is inline — the PM agent walks the user through the PRD section by section and the user signals readiness by continuing to Phase 3. No separate gate prompt is required; the PM's finalize step handles it.

---

## Phase 3: Tech Stack

**Owner:** Architect agent (`bmad-agent-architect` skill)
**Skill:** `bmad-architecture` (stack-scoped pass only — full architecture comes post-approval)
**Input:** Approved PRD
**Output:** `{stack_root}/stack-proposal.md`

### Instructions

1. Invoke the Architect agent (`bmad-agent-architect`). Pass it the PRD path.
2. The Architect produces `{stack_root}/stack-proposal.md` covering:
   - **Frontend** — recommended framework, language, rationale
   - **Backend** — recommended framework, language, rationale
   - **Database** — primary store + rationale; caching layer if applicable
   - **Mobile** — native vs cross-platform recommendation + rationale (omit if not applicable)
   - **Infrastructure** — hosting, CI/CD, containerisation approach
   - **Key libraries/services** — authentication, integrations, and domain-critical services derived from the PRD
   - **Alternatives considered** — at least one per major decision, with why it was not chosen
   - **Constraints** — what this stack rules out for the future
3. Ensure `{stack_root}/` exists. Create it if not.
4. Seed `{stack_root}/rules/` with two files (see **Stack Rules Folder** below) using placeholder content — the content is filled when the user approves.
5. Record the proposal path in `workflow-status.md` under `phase_3.proposal_path`.

### Gate 3 — Stack Approval

```
── GATE 3: TECH STACK REVIEW ─────────────────────────────────────────────────
Stack proposal is ready at: stack/stack-proposal.md

Please review. When ready, reply with one of:
  approved          → stack is locked; stack/rules/ is initialised; proceed to Phase 4
  revise: <notes>   → Architect revises the proposal then re-presents
  stop              → end the workflow here
──────────────────────────────────────────────────────────────────────────────
```

On `approved`:
1. The Architect writes the final, approved stack into `{stack_root}/rules/base-rules.md` (see format below).
2. Write `{stack_root}/rules/client-rules.md` with the starter template (see below) if it does not already exist.
3. Write `{stack_root}/stack-proposal.md` frontmatter `status: approved`.
4. Log: `memlog.py append --type decision --text "Phase 3 complete: stack approved; base-rules.md written"`.

---

## Stack Rules Folder

`{stack_root}/rules/` holds two files that govern how all code in this project is written.

### `base-rules.md` — generated and locked by the Architect on stack approval

```markdown
---
title: Base Coding Rules — {project_name}
status: approved
approved_date: {date}
owner: Architect
---

# Base Coding Rules

> Generated from the approved tech stack. Do not edit without Architect sign-off.
> To add project- or client-specific rules, use client-rules.md.

## Stack

| Layer | Technology | Version / Constraint |
|---|---|---|
| (filled by Architect) | | |

## Language & Style

- (Architect fills: language versions, type-checking policy, linting rules, formatter)

## Architecture Constraints

- (Architect fills: forbidden patterns, required patterns, module boundary rules)

## Naming Conventions

- (Architect fills: files, folders, components, API routes, DB tables)

## Testing Requirements

- (Architect fills: minimum coverage, test types required, what must be integration- vs unit-tested)

## Security Baselines

- (Architect fills: auth approach, input validation policy, secrets handling)

## Dependency Policy

- (Architect fills: allowed registries, review requirements for new deps, banned libs)
```

### `client-rules.md` — user-owned, never overwritten by agents

```markdown
---
title: Client & Project-Specific Rules — {project_name}
owner: You
---

# Client & Project-Specific Rules

> This file is yours. Agents read it but never overwrite it.
> Add rules here that come from your client, organisation, or personal preferences.
> These rules are applied on top of base-rules.md — they do not replace it.

## Client Requirements

<!-- Example: "All API responses must include a request-id header per client logging standard." -->

## Organisation Conventions

<!-- Example: "Use kebab-case for all route paths." -->

## Preferences

<!-- Example: "Prefer composition over inheritance in all component design." -->

## Overrides to Base Rules

<!-- If a base rule conflicts with a client requirement, document the override here with a reason. -->
```

---

## Phase 4: UX Design

**Owner:** UX Designer agent (`.claude/agents/ux-designer.md`)
**Skill:** `bmad-ux`
**Input:** Approved PRD + approved stack
**Output:** `{planning_artifacts}/ux/ux-{project_name}-{date}/`

### Instructions

1. Invoke the UX Designer agent. Pass it the PRD path and the approved `stack/rules/base-rules.md`.
2. The UX Designer derives surfaces and personas directly from the approved PRD — do not assume a fixed set of screens. For each identified surface:
   - Enumerate all screens/views required by the PRD requirements.
   - For each screen: screen name, entry point, components/elements, interaction rules, edge cases, and any privacy or accessibility constraints.
3. Organise outputs under `{planning_artifacts}/ux/ux-{project_name}-{date}/` with one file per major flow or surface.
4. Record the UX output path in `workflow-status.md` under `phase_4.ux_path`.

### Gate 4 — Design Approval

```
── GATE 4: UX DESIGN REVIEW ──────────────────────────────────────────────────
UX specifications are ready at: {planning_artifacts}/ux/ux-{project_name}-{date}/

Please review the screen designs. When ready, reply with one of:
  approved          → proceed to Phase 5 (Epics & Stories)
  revise: <notes>   → UX Designer revises and re-presents
  stop              → end the workflow here
──────────────────────────────────────────────────────────────────────────────
```

Do not proceed until the user replies `approved`. On `revise`, the UX Designer applies the notes and re-presents; one revision cycle before escalating.

---

## Phase 5: Epics & Stories

**Owner:** Business Analyst agent (`.claude/agents/business-analyst.md`)
**Skill:** `bmad-create-epics-and-stories`
**Input:** Approved PRD + approved UX specifications
**Output:** `{planning_artifacts}/epics/epics-{project_name}-{date}.md`

### Instructions

1. Invoke the Business Analyst agent. Pass it the PRD path and UX output path.
2. The BA agent runs `bmad-create-epics-and-stories`:
   - Derives epics from the PRD's functional requirement groups — do not impose a fixed epic structure.
   - Each epic contains user stories in the form: `As a <persona>, I want <action>, so that <outcome>`.
   - Each story includes: acceptance criteria (testable), dependencies, and estimated complexity (S/M/L).
   - Stories are sequenced within each epic to respect technical dependencies.
3. Record the epics path in `workflow-status.md` under `phase_5.epics_path`.
4. Log completion: `memlog.py append --type event --text "Phase 5 complete: epics and stories written at <path>"`.
5. Immediately proceed to **Phase 6: Confluence Push** — no gate between Phase 5 and Phase 6.

---

## Phase 6: Confluence Push (Atlassian Rovo)

**Owner:** This workflow (orchestrator level — no agent delegation needed)
**Trigger:** Automatic after Phase 5 completes
**Input:** All approved planning artefacts + `{project-root}/.confluence-config.toml`
**Output:** Confluence pages created/updated; URLs recorded in `workflow-status.md`
**MCP tools used:** `mcp__claude_ai_Atlassian_Rovo__createConfluencePage`, `mcp__claude_ai_Atlassian_Rovo__updateConfluencePage`, `mcp__claude_ai_Atlassian_Rovo__searchConfluenceUsingCql`

### Pre-flight

1. Read `{project-root}/.confluence-config.toml`. If it does not exist or `enabled = false`, skip Phase 6 and proceed to Phase 7 — log the skip.
2. Both Confluence and Jira are served by the same `claude.ai Atlassian Rovo` MCP server. If the MCP tools are unavailable, skip both Phase 6 and Phase 7 and flag: "Atlassian Rovo MCP not connected — Confluence and Jira push skipped. Run /mcp and verify the claude.ai Atlassian Rovo server is connected."

### Push sequence

Push each enabled document as a Confluence page. Use the `space_key` and optional `parent_page_id` from the config. Page titles follow the pattern `{project_name} — {Document Type}`.

| Document | Config flag | Source path | Confluence page title |
|---|---|---|---|
| Brief | `push_brief` | `phase_1.workspace/brief.md` | `{project_name} — Product Brief` |
| PRD | `push_prd` | `phase_2.prd_path` | `{project_name} — PRD` |
| Tech Stack | `push_stack` | `{stack_root}/stack-proposal.md` | `{project_name} — Tech Stack` |
| UX Specs | `push_ux` | `phase_4.ux_path/*.md` (one page per file) | `{project_name} — UX: {flow name}` |
| Epics & Stories | `push_epics` | `phase_5.epics_path` | `{project_name} — Epics & Stories` |

**For each enabled document:**
1. Read the source file(s) from disk.
2. Check if a page with the same title already exists in the space using `mcp__claude_ai_Atlassian_Rovo__searchConfluenceUsingCql` with query `title = "{page_title}" AND space = "{space_key}"`.
3. If the page exists, call `mcp__claude_ai_Atlassian_Rovo__updateConfluencePage` with the existing page ID and the new content.
   If the page does not exist, call `mcp__claude_ai_Atlassian_Rovo__createConfluencePage` with:
   - `spaceId`: the ID of the space matching `confluence_config.space_key` (resolve via `mcp__claude_ai_Atlassian_Rovo__getConfluenceSpaces` on first use)
   - `parentId`: from `confluence_config.parent_page_id` (if set)
   - `title`: as per table above
   - `body`: document content (markdown rendered as best-effort Confluence storage format)
4. Capture the returned page URL.
5. Record in `workflow-status.md` under `phase_6.confluence_pages[].url`.

### On partial failure

If one page fails to push: log the failure, continue with remaining documents, and report all failures in the final summary. Do not halt the whole push for one failure.

### Gate 6 — Confluence Push Summary

```
── GATE 6: CONFLUENCE PUSH COMPLETE ──────────────────────────────────────────
Pushed to Confluence space: {confluence_config.space_key}

  Pages created/updated: N
  Failures:              N  (listed below if any)

Pages:
  - {project_name} — Product Brief: <url>
  - {project_name} — PRD: <url>
  - {project_name} — Tech Stack: <url>
  - {project_name} — UX: <flow>: <url>  (one line per file)
  - {project_name} — Epics & Stories: <url>

Failures (if any):
  - [document name]: <error>
──────────────────────────────────────────────────────────────────────────────
```

Log: `memlog.py append --type event --text "Phase 6 complete: N pages pushed to Confluence space {space_key}"`.

Proceed automatically to **Phase 7: Jira Push**.

---

## Phase 7: Jira Push (Atlassian Rovo)

**Owner:** This workflow (orchestrator level — no agent delegation needed)
**Trigger:** Automatic after Phase 6 completes (or after Phase 5 if Phase 6 was skipped)
**Input:** `{planning_artifacts}/epics/epics-{project_name}-{date}.md` + `{project-root}/.jira-config.toml`
**Output:** Jira epics and stories created; URLs recorded in `workflow-status.md`
**MCP tools used:** `mcp__claude_ai_Atlassian_Rovo__createJiraIssue`, `mcp__claude_ai_Atlassian_Rovo__getJiraProjectIssueTypesMetadata`

### Pre-flight

1. Read `{project-root}/.jira-config.toml`. If it does not exist or `enabled = false`, skip Phase 7 and go to **Planning Complete** — log the skip.
2. MCP connectivity was already verified in Phase 6 pre-flight. If Phase 6 was skipped due to MCP unavailability, skip Phase 7 as well.
3. Call `mcp__claude_ai_Atlassian_Rovo__getJiraProjectIssueTypesMetadata` for `jira_config.project_key` to confirm the project exists and to resolve the correct issue type IDs for `Epic` and `Story` before pushing. Use the returned IDs in all subsequent `createJiraIssue` calls.

### Push sequence

Parse the approved epics file. For each epic and its stories, push to Jira in order:

**For each Epic:**
1. Call `mcp__claude_ai_Atlassian_Rovo__createJiraIssue` with:
   - `projectKey`: from `jira_config.project_key`
   - `issueType`: `Epic` (use the resolved issue type ID from pre-flight)
   - `summary`: epic title
   - `description`: epic description + acceptance criteria
   - `labels`: from `jira_config.default_labels` (omit field if list is empty)
2. Capture the returned Jira issue key (e.g. `PROJ-1`) and URL.
3. Record in `workflow-status.md` under `phase_7.epics[].jira_key`.

**For each Story under the Epic:**
1. Call `mcp__claude_ai_Atlassian_Rovo__createJiraIssue` with:
   - `projectKey`: from `jira_config.project_key`
   - `issueType`: `Story` (use the resolved issue type ID from pre-flight)
   - `summary`: story title
   - `description`: user story text + acceptance criteria
   - `parent`: the Jira key of the parent epic created above
   - `storyPoints`: mapped from complexity (S=1, M=3, L=5) if `jira_config.map_complexity` is true; omit field otherwise
   - `labels`: same as parent epic (omit if empty)
2. Capture the returned Jira issue key and URL.
3. Record in `workflow-status.md` under `phase_7.epics[].stories[].jira_key`.

### On partial failure

If one issue fails to create: log the failure, continue with remaining issues, and report all failures in the final summary. Do not halt the whole push for one failure.

### Gate 7 — Jira Push Summary

```
── GATE 7: JIRA PUSH COMPLETE ────────────────────────────────────────────────
Pushed to Jira project: {jira_config.project_key}

  Epics created:   N
  Stories created: N
  Failures:        N  (listed below if any)

View in Jira: {jira_config.board_url}

Failures (if any):
  - [epic/story title]: <error>
──────────────────────────────────────────────────────────────────────────────
```

Log: `memlog.py append --type event --text "Phase 7 complete: N epics, N stories pushed to Jira project {project_key}"`.

---

## Confluence Configuration File

Create `{project-root}/.confluence-config.toml` to enable Confluence push. Add to `.gitignore` if it contains sensitive values (it uses MCP credentials, not raw tokens, so usually safe to commit).

```toml
# .confluence-config.toml — Confluence push configuration
# Read by sdlc-planning-workflow after Phase 5.

[confluence_config]

# Set to false to skip Confluence push entirely.
enabled = true

# Your Confluence space key (e.g. "PROJ", "TEAM", "ENG").
space_key = "PROJ"

# Optional: page ID to create all documents under as children.
# Leave empty to create at the space root.
parent_page_id = ""

# Which planning documents to push. Set individual flags to false to skip.
push_brief  = true
push_prd    = true
push_stack  = true
push_ux     = true
push_epics  = true
```

---

## Jira Configuration File

Create `{project-root}/.jira-config.toml` to enable Jira push. Add to `.gitignore` if it contains sensitive values.

```toml
# .jira-config.toml — Jira push configuration
# Read by sdlc-planning-workflow after Phase 6 (or Phase 5 if Confluence skipped).

[jira_config]

# Set to false to skip Jira push entirely.
enabled = true

# Your Jira project key (e.g. "PROJ", "APP", "ENG").
project_key = "PROJ"

# Your Jira board URL — shown in the push summary for quick access.
board_url = "https://your-org.atlassian.net/jira/software/projects/PROJ/boards"

# Map story complexity (S/M/L) to story points. Set to false to omit story points.
map_complexity = true

# Labels applied to every issue pushed. Use project-specific values.
default_labels = []

# Whether to create Epics using Jira's native Epic issue type (true)
# or as a parent Story (false, for older Jira configurations).
use_epic_issue_type = true
```

---

## Planning Complete

When Phase 7 is done (or skipped):

1. Update `{planning_artifacts}/workflow-status.md` — set `status: complete`.
2. Present the user with a summary:

```
── PLANNING COMPLETE ──────────────────────────────────────────────────────────
All planning artefacts are ready. The Development & Testing workflow is the next step.

  Brief:            {planning_artifacts}/briefs/...
  PRD:              {planning_artifacts}/prd/...
  Tech Stack:       stack/stack-proposal.md
  Coding Rules:     stack/rules/base-rules.md
  Client Rules:     stack/rules/client-rules.md  ← add your overrides here before building
  UX Specs:         {planning_artifacts}/ux/...
  Epics & Stories:  {planning_artifacts}/epics/...

  Confluence:       {confluence_config.space_key} space  (if push was enabled)
  Jira Board:       {jira_config.board_url}              (if push was enabled)

Next steps:
  /sdlc-dev-workflow      → development and testing workflow (when available)
  /bmad-sprint-planning   → gate the epics against implementation readiness
──────────────────────────────────────────────────────────────────────────────
```

---

## Workflow Status File

Maintained at `{planning_artifacts}/workflow-status.md`. Written after each phase and gate.

```markdown
---
project: {project_name}
started: {date}
status: in-progress   # in-progress | complete | stopped
last_completed_phase: 0
---

## Phase Status

| Phase | Status | Artefact Path | Gate | Gate Status |
|---|---|---|---|---|
| 1 — Brief | pending | | Brief Approval | pending |
| 2 — PRD | pending | | (inline) | pending |
| 3 — Stack | pending | | Stack Approval | pending |
| 4 — UX Design | pending | | Design Approval | pending |
| 5 — Epics & Stories | pending | | (none) | — |
| 6 — Confluence Push | pending | | Push Summary | pending |
| 7 — Jira Push | pending | | Push Summary | pending |

## Confluence Push Results

| Document | Confluence URL | Status |
|---|---|---|

## Jira Push Results

| Epic | Jira Key | Stories Pushed | Failures |
|---|---|---|---|
```

---

## Stop Conditions (Any Phase)

- The user replies `stop` at any gate.
- A source artefact required by the current phase does not exist on disk.
- The current agent exhausts its retry limit without producing output.
- A human decision is required that no agent can make (business, legal, budget).

On any stop: write current state to `workflow-status.md`, tell the user where things stand and what the next action would be to resume, then halt.

---

## Resuming a Stopped Workflow

On activation, if `workflow-status.md` shows `status: in-progress`, offer to resume:
- Read `last_completed_phase`.
- Skip all completed phases.
- Begin from the next phase using existing artefacts as inputs.
- Re-present the pending gate if it was not yet resolved.
