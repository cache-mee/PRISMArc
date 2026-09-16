# PRISM Setup Guide

> Step-by-step setup for every role. Follow **Part A (Common)** first, then the section for your role.

---

## Part A — Common Setup (Everyone)

Every team member needs the following regardless of role.

### A1. Install Claude Code

Claude Code is the AI shell you run PRISM commands from.

1. Install from [claude.ai/code](https://claude.ai/code) — choose the **VS Code extension** or the **desktop app**.
2. Sign in with your Anthropic account.
3. Open the project repository folder in VS Code (or set it as the working directory in the desktop app).

### A2. Connect Atlassian Rovo MCP

This gives Claude Code access to Jira and Confluence.

1. In Claude Code, type `/mcp`
2. Select **claude.ai Atlassian Rovo**
3. Click **Needs Auth** — a browser tab will open
4. Sign in with your **Atlassian account** (the one that has access to your Jira/Confluence workspace)
5. Authorise the connection
6. Return to Claude Code and click **Check connection**

> **If no browser opens:** The OAuth URL isn't launching. Open your Windows default browser settings (Settings → Apps → Default apps → Web browser) and set a browser, then retry. Alternatively, use the Claude Code **desktop app** instead of the VS Code extension.

**Verify it works:**
Ask Claude Code: *"List the Jira projects I have access to"* — it should return your project list.

### A3. Confirm your Atlassian workspace

Jira and Confluence push targets are set in two config files at the repo root:

**`.jira-config.toml`** — update these values:
```toml
[jira_config]
project_key = "SALON"          # ← your Jira project key
board_url   = "https://experionglobal.atlassian.net/jira/software/projects/SALON/boards"
```

**`.confluence-config.toml`** — update these values:
```toml
[confluence_config]
space_key      = "PROJ"        # ← your Confluence space key
parent_page_id = ""            # ← optional: page ID to nest docs under
```

> **How to find your Confluence space key:** Go to your Confluence space → look at the URL: `.../wiki/spaces/PROJ/...` — `PROJ` is the key.

> **How to find a parent page ID:** Open the page in Confluence → look at the URL: `.../pages/123456/...` — `123456` is the ID.

---

## Part B — Role-Specific Setup

---

### Role: Business Analyst (BA)

**What you do in PRISM:** Run the planning workflow to take ideas through discovery, brief, and epics.

#### Additional setup: none beyond Part A.

#### Your primary commands:

```
/sdlc-planning-workflow         Start planning a new feature or initiative
/workflow-status                See where planning stands
```

#### Workflow you own:
- **`sdlc-planning-workflow`** — Phases 1 (Brief) and 5 (Epics & Stories)

#### Tips:
- The BA agent will ask you clarifying questions during Phase 1. Answer as thoroughly as you can — vague inputs produce vague briefs.
- During Phase 5, review the epics carefully before approving. Story sizing (S/M/L) maps to Jira story points, so inaccurate sizing affects sprint planning.
- If you want to resume a stopped planning session: just run `/sdlc-planning-workflow` again — it will detect the in-progress run and offer to resume.

---

### Role: Product Manager (PM)

**What you do in PRISM:** Own the PRD phase within the planning workflow.

#### Additional setup: none beyond Part A.

#### Your primary commands:

```
/sdlc-planning-workflow         Run (or resume) the planning pipeline
/workflow-status                Check planning phase status
```

#### Workflow you own:
- **`sdlc-planning-workflow`** — Phase 2 (PRD)

#### Tips:
- The PM agent resolves every `[ASSUMPTION]` tag from the brief by asking you questions. Provide real answers — the PRD is the source of truth for the entire downstream pipeline.
- The PRD review is inline (the agent walks you through section by section). When you're satisfied, say "proceed" or "continue" — no separate gate prompt.
- Out-of-scope items are as important as in-scope items. Be explicit.

---

### Role: Architect

**What you do in PRISM:** Approve the tech stack and lock the coding rules.

#### Additional setup: none beyond Part A.

#### Your primary commands:

```
/sdlc-planning-workflow         Run (or resume) the planning pipeline
/workflow-status                Check planning phase status
```

#### Workflow you own:
- **`sdlc-planning-workflow`** — Phase 3 (Tech Stack)

#### Tips:
- The Architect agent produces `stack/stack-proposal.md`. Review it carefully before approving — once approved, it becomes `stack/rules/base-rules.md` which governs all code written by the Developer agent.
- Add project-specific overrides to `stack/rules/client-rules.md` (this file is yours — agents read it but never overwrite it).
- If the stack needs to change later: update `base-rules.md` and write an ADR in `docs/adr/` explaining why.

---

### Role: UX Designer

**What you do in PRISM:** Design screen specifications for every surface the PRD requires.

#### Additional setup: none beyond Part A.

#### Your primary commands:

```
/sdlc-planning-workflow         Run (or resume) the planning pipeline
/workflow-status                Check planning phase status
```

#### Workflow you own:
- **`sdlc-planning-workflow`** — Phase 4 (UX Design)

#### Tips:
- The UX Designer agent derives surfaces and screens from the approved PRD — it does not assume a fixed set of screens. Check the PRD is complete before Phase 4 runs.
- Review the UX output folder (`bmad-output/planning-artifacts/ux/`) for one file per major flow. Request revisions with `revise: <specific notes>` at the gate.
- UX specs feed directly into the Developer agent's context during implementation — be precise about component names, interaction rules, and edge cases.

---

### Role: Developer

**What you do in PRISM:** Implement Jira tickets using the dev workflow, write unit tests afterward.

#### Additional setup required:

**1. Install Git** (if not already installed)
```
winget install --id Git.Git
```
Verify: `git --version`

**2. Configure Git identity**
```
git config --global user.name "Your Name"
git config --global user.email "you@company.com"
```

**3. Install GitHub CLI**
```
winget install --id GitHub.cli --accept-source-agreements --accept-package-agreements
```
Restart your terminal after installation.

**4. Authenticate GitHub CLI**

Open a terminal (not Claude Code) and run:
```
gh auth login
```
Select: `GitHub.com` → `HTTPS` → `Login with a web browser`
Copy the code shown, press Enter, paste it in your browser and authorise.

Verify: `gh auth status` — should show your GitHub username as active.

**5. Confirm repo access**
```
git ls-remote origin
```
Should list branches. If you get "Repository not found": ask the repo owner to add you as a collaborator at `github.com/{owner}/{repo}/settings/access`.

#### Your primary commands:

```
/sdlc-dev-workflow PROJ-42          Start work on a ticket
/sdlc-dev-workflow review PROJ-42   Run code review (open a NEW session first)
/sdlc-unit-test-workflow PROJ-42    Write unit tests after review passes
/workflow-status PROJ-42            Check where this ticket stands
```

#### Workflows you own:
- **`sdlc-dev-workflow`** — full development pipeline for a ticket
- **`sdlc-unit-test-workflow`** — unit test authoring after implementation

#### Tips:
- Always start a **new Claude Code session** for the code review phase — the reviewer agent must see only the diff, not the implementation conversation.
- At the commit message gate: use `edit: <your message>` if the suggested message isn't quite right. Good commit messages matter for the reviewer.
- At the push gate: always confirm what commits will be pushed before replying `push`.
- If implementation reveals a scope issue: stop the workflow, update the implementation plan, and re-present it to yourself before continuing.

---

### Role: QA Engineer

**What you do in PRISM:** Run integration tests against the developer's PR and return a PASS or FAIL verdict to Jira.

#### Additional setup required:

**1. Install Git** (if not already installed — same as Developer step 1)

**2. Install GitHub CLI** (same as Developer steps 3–5)

**3. Clone the repository** (if working from a different machine)
```
git clone https://github.com/{owner}/{repo}.git
cd {repo}
```

**4. Connect Atlassian Rovo MCP** (same as Part A2)

**5. Confirm PR access**
```
gh pr list
```
Should list open PRs. If not: ask the repo owner to add you as a collaborator (read access is sufficient for QA).

#### Your primary commands:

```
/sdlc-qa-workflow PROJ-42          Run integration tests for a ticket
/workflow-status PROJ-42           Check ticket status before starting
/workflow-status                   See all tickets awaiting QA
```

#### Workflow you own:
- **`sdlc-qa-workflow`** — integration test design, execution, and Jira verdict

#### Tips:
- Check `/workflow-status` first to see which tickets are awaiting QA (status = `unit-testing complete`).
- The QA agent writes and runs integration tests automatically — your job is to approve the test plan (Gate 2) before any tests are written.
- If tests fail: the agent comments on the PR and transitions Jira to "Needs Work" automatically. The developer must fix and re-raise before QA re-runs.
- You do **not** need the `.orchestration/runs/` folder to run QA — you just need the ticket key and PR URL. The workflow can operate without the run directory.
- Do not mock your own database in integration tests — the QA agent is instructed not to, but verify this in the test plan before approving.

---

## Part C — Troubleshooting

### "Rovo MCP says Needs Auth even after I authenticated"

The auth cache may be stale. In Claude Code, run:
```
# Ask Claude Code to clear the MCP auth cache
```
Or manually delete: `C:/Users/{you}/.claude/mcp-needs-auth-cache.json` and restart Claude Code.

### "gh: command not found after installation"

The PATH hasn't refreshed. Close and reopen your terminal (or restart VS Code). If it still doesn't work:
```
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
```

### "git ls-remote: Repository not found"

You haven't been added as a collaborator. Ask the repo owner to go to:
`github.com/{owner}/{repo}/settings/access` → Add people → your GitHub username → Write role.

### "The planning workflow can't find config.yaml"

The BMAD config file is missing. Create it at `_bmad/bmm/config.yaml`:
```yaml
user_name: "Your Name"
project_name: "salon-app"
communication_language: "English"
planning_artifacts: "bmad-output/planning-artifacts"
```

### "Confluence push failed — space not found"

Check that `space_key` in `.confluence-config.toml` matches exactly (case-sensitive) the key shown in your Confluence space URL.

### "Jira push created epics but stories have no parent"

Your Jira project may use an older Epic Link field instead of the native parent. Set `use_epic_issue_type = false` in `.jira-config.toml`.

---

## Part D — File Reference

| File | Purpose | Who edits it |
|---|---|---|
| `.jira-config.toml` | Jira project key, board URL, labels | PM / BA |
| `.confluence-config.toml` | Confluence space, parent page | PM / BA |
| `stack/rules/base-rules.md` | Coding rules — locked by Architect | Architect only |
| `stack/rules/client-rules.md` | Project overrides | Anyone |
| `.orchestration/PROJECT-STATUS.md` | Project-wide lifecycle dashboard | Auto-updated by workflows |
| `.orchestration/runs/{TICKET}/current.md` | 7-line "you are here" pointer | Auto-updated by workflows |
| `.orchestration/runs/{TICKET}/status.md` | Full ticket lifecycle detail | Auto-updated by workflows |
| `docs/prism/PRISM-Overview.md` | This system explained with example | Team |
| `docs/prism/PRISM-Setup-Guide.md` | This file | Team |
