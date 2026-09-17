# Implementation Plan: 0.2 Frontend project scaffolding

> **Instructions for the agent filling this template:**
> Replace every `{placeholder}` with real content. Delete sections marked optional if not applicable.
> This plan must be presented to the user for approval before any code is written.

---

## Ticket Reference

| Field | Value |
|---|---|
| Jira Ticket | `APPOINTMEN-10` |
| Type | `Story` |
| Branch | `feature/APPOINTMEN-10-02-frontend-project-scaffolding` |
| Assigned to | `sparc.team_25@experionglobal.com` |

**Priority:** Medium

**Ticket description (verbatim):** "As a developer, I want B2B_FE/ initialized per the approved layout
with a trivial rendered page, so there is a running React app to build every frontend-facing story
against."

**Acceptance criteria (verbatim):** "package.json (React 18+, TypeScript 5+, Vite 5+); Dockerfile builds
the app; tsconfig strict:true; src/ skeleton (chat/, dashboard/, shared/, api/); eslint+prettier
configured; tests/ skeleton (Vitest+RTL path wired); dev server renders a trivial placeholder page in a
browser."

**Classification:** Frontend-only, per `CLAUDE.md` → *Repository layout*. Every file in this plan lives
under `B2B_FE/`. No `B2B_BE/` file is touched.

---

## Overview

Initialize `B2B_FE/` from scratch as a Vite + React + TypeScript application, matching the structure and
versions locked in `stack/rules/base-rules.md` (itself derived from the approved `stack/stack-proposal.md`
§9). This delivers exactly the ticket's acceptance criteria: a buildable, lintable, strictly-typed React
app with the four prescribed `src/` domain folders (`chat/`, `dashboard/`, `shared/`, `api/`) as empty
skeletons, a Vitest+React Testing Library test path wired with one smoke test, a working `Dockerfile`, and
a dev server that renders a trivial placeholder page in a browser. No feature code (actual chat UI,
dashboard UI, or backend integration) is built — this ticket only stands up the scaffold every later
frontend story will build on.

---

## Business Context

The repository currently contains no application source code (`CLAUDE.md` → *Application status*):
`B2B_FE/` does not exist on disk at all (verified — `ls B2B_FE` fails with "No such file or directory").
Every subsequent frontend-facing story (Web Chat widget, Owner Dashboard) needs a running, conventionally
structured React app to build against; this ticket is that foundation. The user-facing outcome for this
ticket specifically is developer-facing, not end-user-facing: a `npm install && npm run dev` (or
equivalent) that renders a trivial placeholder page in a browser, proving the toolchain (Vite, TypeScript
strict mode, ESLint/Prettier, Vitest+RTL, Docker build) is wired correctly before any real feature work
starts.

---

## Technical Context

Technical approach is fixed by the already-approved stack, not re-derived:

- **Stack** (`stack/rules/base-rules.md` → *Stack* table): React 18+, TypeScript 5+, Vite 5+, one
  codebase serving both the Web Chat widget and the Owner Dashboard.
- **Repository layout** (`stack/rules/base-rules.md` → *Architecture Constraints*, reproduced from
  `stack/stack-proposal.md` §9) is the **binding**, not illustrative, structure:
  ```text
  B2B_FE/
    package.json
    Dockerfile
    src/
      chat/
      dashboard/
      shared/
      api/
    tests/
  ```
  New top-level folders under `B2B_FE/src/` beyond this tree require an Architect decision — none are
  introduced by this plan.
- **Language & Style** (`stack/rules/base-rules.md` → *Language & Style*, Frontend):
  - TypeScript strict mode (`"strict": true`) — no `any` used to bypass typing.
  - Function components with hooks only; no class components.
  - Formatter: `prettier` (default settings). Linter: `eslint` with
    `@typescript-eslint/recommended` + `eslint-plugin-react-hooks`. No hand-rolled custom rule set.
  - API calls go through a typed client in `B2B_FE/src/api/` — no ad-hoc `fetch`/`axios` in components.
    For this ticket, `src/api/` is scaffolded as an empty, committed placeholder only (no backend exists
    yet to call).
- **Testing** (`stack/rules/base-rules.md` → *Testing Requirements*): no test framework is mandated
  beyond what Vite/React ship with by default; if frontend tests are written, use **Vitest + React Testing
  Library** — not a second, heavier runner. This ticket's AC explicitly requires the Vitest+RTL path to be
  wired, so one trivial smoke test is included to prove the path works end-to-end (not a coverage
  requirement).
- **Infra** (`stack/rules/base-rules.md` → *Stack* table / `stack-proposal.md` §5): one `Dockerfile` in
  `B2B_FE/` building the app. The root `docker-compose.yml` (orchestrating backend + frontend + Postgres)
  is explicitly **out of scope** for this ticket — it is a separate cross-cutting concern, not part of
  "frontend project scaffolding," and touching it would require coordination with the backend scaffolding
  ticket.
- **Naming conventions** (`stack/rules/base-rules.md` → *Naming Conventions*, Frontend): lowercase,
  kebab-case for multi-word component folders; PascalCase for component filenames (e.g. `App.tsx`);
  camelCase for hooks/utility modules.
- `stack/rules/client-rules.md` has no recorded client-specific overrides as of this plan — base rules
  apply unmodified.

No architecture decision is required for this ticket: the folder tree, versions, and tooling are already
fully specified by `base-rules.md`; this plan only sequences their creation.

---

## Affected Areas

All paths are **NEW** — `B2B_FE/` does not exist on disk (confirmed via direct filesystem check before
writing this plan).

| Area | Change Type | Reason |
|---|---|---|
| `B2B_FE/package.json` | New | Project manifest — React 18+, TypeScript 5+, Vite 5+, ESLint/Prettier, Vitest+RTL dependencies and scripts. |
| `B2B_FE/tsconfig.json` / `B2B_FE/tsconfig.node.json` | New | TypeScript config with `"strict": true`, per base-rules.md. |
| `B2B_FE/vite.config.ts` | New | Vite build/dev-server config, with Vitest test config attached (`test` block). |
| `B2B_FE/index.html` | New | Vite entry HTML shell. |
| `B2B_FE/src/main.tsx` | New | React app bootstrap (mounts `App` into `index.html`'s root element). |
| `B2B_FE/src/App.tsx` | New | Trivial placeholder page component satisfying the "dev server renders a trivial placeholder page" AC. |
| `B2B_FE/src/chat/.gitkeep` (or `README.md`) | New | Empty domain-folder skeleton per the enforced tree — Web Chat widget UI lands here in later stories. |
| `B2B_FE/src/dashboard/.gitkeep` (or `README.md`) | New | Empty domain-folder skeleton — Owner Dashboard UI lands here in later stories. |
| `B2B_FE/src/shared/.gitkeep` (or `README.md`) | New | Empty domain-folder skeleton — shared components/hooks land here in later stories. |
| `B2B_FE/src/api/.gitkeep` (or `README.md`) | New | Empty domain-folder skeleton — typed backend API client lands here once `B2B_BE/` exposes endpoints. |
| `B2B_FE/.eslintrc.cjs` (or `eslint.config.js`, per current ESLint major version conventions) | New | ESLint config: `@typescript-eslint/recommended` + `eslint-plugin-react-hooks`. |
| `B2B_FE/.prettierrc` | New | Prettier config, default settings. |
| `B2B_FE/.prettierignore` / `.eslintignore` (or `ignorePatterns` in flat config) | New | Standard build-output exclusions (`dist/`, `node_modules/`). |
| `B2B_FE/tests/App.test.tsx` | New | Vitest + RTL smoke test proving the test path is wired (renders `App`, asserts placeholder content is present). |
| `B2B_FE/tests/setup.ts` | New | RTL/jest-dom test setup file, referenced from `vite.config.ts`'s `test.setupFiles`. |
| `B2B_FE/Dockerfile` | New | Multi-stage build (install deps, `vite build`) producing a servable static build, per base-rules.md Infra row. |
| `B2B_FE/.dockerignore` | New | Excludes `node_modules/`, `dist/` etc. from the Docker build context. |
| `B2B_FE/.gitignore` | New | Standard Node/Vite ignores (`node_modules/`, `dist/`, `.env`). |
| `B2B_FE/.env.example` | New | Empty/placeholder — no frontend secrets are known yet; kept for convention parity with base-rules.md's Security Baselines pattern, populated by later tickets if a frontend env var is ever needed. |

---

## Tasks

> Each task must be completable independently and produce a testable outcome.
> Order tasks to respect technical dependencies (data layer before business logic before UI).

### Task 1: Scaffold Vite + React + TypeScript project

**Description:** Initialize `B2B_FE/` as a Vite React-TS project (React 18+, TypeScript 5+, Vite 5+),
producing a working `package.json`, `tsconfig.json`, `vite.config.ts`, `index.html`, `src/main.tsx`, and a
placeholder `src/App.tsx`. Confirms `npm run dev` serves a page and `npm run build` succeeds before any
further structure is layered on.

**Files to modify:** None (first task in an empty folder).

**New files to create:**
- `B2B_FE/package.json` — scripts: `dev`, `build`, `preview` (Vite defaults) plus placeholders for `lint`,
  `format`, `test` wired in later tasks.
- `B2B_FE/tsconfig.json`, `B2B_FE/tsconfig.node.json` — base compiler config (strict mode deferred to
  Task 2 to keep this task's diff minimal, but may be set here directly if the Vite React-TS template
  already defaults to `strict: true`, in which case Task 2 only verifies it).
- `B2B_FE/vite.config.ts`
- `B2B_FE/index.html`
- `B2B_FE/src/main.tsx`
- `B2B_FE/src/App.tsx` — trivial placeholder content only (e.g. a heading identifying the app), no
  feature UI.
- `B2B_FE/.gitignore`

**Dependencies:** None

**Complexity:** `Low`

**Testing requirements:**
- Evidence: `npm run build` exits 0 from `B2B_FE/`.
- Evidence: `npm run dev` starts the dev server without error (process starts, listens on a port); manual
  or scripted check that the placeholder page renders in a browser (satisfies the AC's "dev server renders
  a trivial placeholder page in a browser").

**Documentation updates:** None.

---

### Task 2: Enforce TypeScript strict mode

**Description:** Set `"strict": true` explicitly in `B2B_FE/tsconfig.json` (and confirm `tsconfig.node.json`
does not relax it), per base-rules.md's Frontend Language & Style rule. Run the TypeScript compiler in
no-emit mode to confirm the scaffolded code (Task 1's `App.tsx`/`main.tsx`) type-checks cleanly under
strict mode.

**Files to modify:**
- `B2B_FE/tsconfig.json`

**New files to create:** None

**Dependencies:** Task 1

**Complexity:** `Low`

**Testing requirements:**
- Evidence: `tsc --noEmit` (or the equivalent `npm run typecheck` if added) exits 0.

**Documentation updates:** None.

---

### Task 3: Create `src/` domain skeleton (`chat/`, `dashboard/`, `shared/`, `api/`)

**Description:** Add the four empty domain folders required by the enforced tree in base-rules.md /
stack-proposal.md §9. Since git does not track empty directories, each gets a minimal placeholder file
(`.gitkeep` or a one-line `README.md` stating the folder's purpose) so the structure is committed and
visible, without adding any feature code.

**Files to modify:** None

**New files to create:**
- `B2B_FE/src/chat/.gitkeep`
- `B2B_FE/src/dashboard/.gitkeep`
- `B2B_FE/src/shared/.gitkeep`
- `B2B_FE/src/api/.gitkeep`

**Dependencies:** Task 1

**Complexity:** `Low`

**Testing requirements:**
- Evidence: directory listing (`ls B2B_FE/src`) shows all four folders present; no build/test tooling
  exercises empty folders, so no additional automated check applies.

**Documentation updates:** None.

---

### Task 4: Configure ESLint + Prettier

**Description:** Add ESLint (`@typescript-eslint/recommended` + `eslint-plugin-react-hooks`) and Prettier
(default settings) configuration, matching base-rules.md's Frontend Language & Style rule exactly — no
hand-rolled custom rule set. Wire `lint` and `format` scripts into `package.json`.

**Files to modify:**
- `B2B_FE/package.json` (add `lint`, `format` scripts and devDependencies)

**New files to create:**
- `B2B_FE/.eslintrc.cjs` (or `eslint.config.js` if the installed ESLint major version requires flat
  config — determined at implementation time by the ESLint version Vite's template pulls in)
- `B2B_FE/.prettierrc`
- `B2B_FE/.eslintignore` / `.prettierignore` (or `ignores` entries in flat config)

**Dependencies:** Task 1

**Complexity:** `Low`

**Testing requirements:**
- Evidence: `npm run lint` exits 0 against the Task 1–3 scaffolded files.
- Evidence: `npm run format -- --check` (Prettier check mode) exits 0.

**Documentation updates:** None.

---

### Task 5: Wire Vitest + React Testing Library and add a smoke test

**Description:** Add Vitest and React Testing Library as devDependencies, configure Vitest via the `test`
block in `vite.config.ts` (jsdom environment, `tests/setup.ts` for RTL/jest-dom matchers), and add one
trivial smoke test rendering `App.tsx` and asserting the placeholder content is present. This directly
satisfies the AC's "tests/ skeleton (Vitest+RTL path wired)" — proving the path works, not building a
coverage suite.

**Files to modify:**
- `B2B_FE/vite.config.ts` (add `test` config block)
- `B2B_FE/package.json` (add `test` script, Vitest/RTL devDependencies)

**New files to create:**
- `B2B_FE/tests/setup.ts`
- `B2B_FE/tests/App.test.tsx`

**Dependencies:** Task 1, Task 2

**Complexity:** `Medium` (Vitest/jsdom/RTL wiring is the most failure-prone step in this ticket — config
mismatches between `vite.config.ts`'s `test` block and `tsconfig.json`'s `types` array are the common
failure mode).

**Testing requirements:**
- Evidence: `npm run test` (or `npx vitest run`) exits 0, with the one smoke test passing.

**Documentation updates:** None.

---

### Task 6: Add `Dockerfile` building the app

**Description:** Add a multi-stage `Dockerfile` in `B2B_FE/` (build stage: install deps + `vite build`;
runtime stage: serve the static `dist/` output) per base-rules.md's Infra row ("One `Dockerfile` per
top-level folder"). Add a matching `.dockerignore`. This ticket only requires the Dockerfile to build the
app — it does not require wiring it into the root `docker-compose.yml` (out of scope, see below).

**Files to modify:** None

**New files to create:**
- `B2B_FE/Dockerfile`
- `B2B_FE/.dockerignore`

**Dependencies:** Task 1 (needs a buildable app to build against)

**Complexity:** `Low`

**Testing requirements:**
- Evidence: `docker build -t b2b-fe-scaffold-check B2B_FE` exits 0.

**Documentation updates:** None.

---

### Task 7: Final integration check — full scaffold smoke test

**Description:** With all prior tasks merged, run the complete validation sequence in order (install,
typecheck, lint, format check, test, build, docker build, dev-server manual render check) against the
final state of `B2B_FE/` as a single end-to-end confirmation that every AC is met together, not just
task-by-task in isolation.

**Files to modify:** None (validation-only task; may touch `package.json` scripts if a gap is found
during the end-to-end run, e.g. adding a combined `validate` script).

**New files to create:** None expected.

**Dependencies:** Task 1–6

**Complexity:** `Low`

**Testing requirements:**
- Evidence: `npm ci`, `npm run typecheck`, `npm run lint`, `npm run format -- --check`, `npm run test`,
  `npm run build`, `docker build -t b2b-fe-scaffold-check B2B_FE` — each command and its exit code
  recorded.
- Evidence: dev server (`npm run dev`) confirmed to render the placeholder page in an actual browser
  (screenshot or manual confirmation), since this is the one AC line no automated command alone proves.

**Documentation updates:** None.

---

## External Dependencies

- **npm registry access** — required to install React, Vite, TypeScript, ESLint, Prettier, Vitest, and RTI
  packages. Assumed available in the dev/CI environment; not otherwise verified by this plan.
- **Docker** — required for Task 6/7's `docker build` evidence. Assumed available per base-rules.md's
  Infra row (Docker Compose is the stated infra approach for this project).
- **No backend dependency.** `B2B_BE/` does not exist yet and is not required for this ticket — `src/api/`
  is scaffolded empty, with no live endpoint to call. This is expected and explicitly non-blocking per the
  ticket's own framing ("a running React app to build every frontend-facing story against").
- **No other team's work is a blocker** for this ticket.

---

## Testing Strategy

| Test Type | Scope | Tooling |
|---|---|---|
| Unit / component | One smoke test rendering the placeholder `App` component, proving the Vitest+RTL path is wired (per AC) | Vitest + React Testing Library (`stack/rules/base-rules.md` → Testing Requirements) |
| Integration | Not applicable — no backend, no cross-module behavior exists yet in this ticket | N/A |
| End-to-End *(optional)* | Manual/scripted browser check that `npm run dev` renders the placeholder page | Manual browser check (no E2E framework is mandated or justified for one placeholder page) |
| Build/Lint validation | `tsc --noEmit`, `eslint`, `prettier --check`, `vite build`, `docker build` | npm scripts + Docker CLI |

Minimum coverage expectation: base-rules.md sets **no numeric coverage threshold** for the frontend and
explicitly scopes this PRD's testing to happy-flow-only, prioritized elsewhere (confirm-before-write flows,
conflict detection) — neither applies to this scaffolding ticket. The only testing obligation this ticket
carries is the AC's own: the Vitest+RTL path must be wired and demonstrably working, via exactly one
passing smoke test — not a coverage percentage.

---

## Security Considerations

No secrets, auth, or data-handling code is introduced by this ticket (no backend integration exists yet).
`B2B_FE/.env.example` is added empty/placeholder for convention parity with base-rules.md's Security
Baselines pattern (env vars documented via `.env.example`, real `.env` git-ignored) so that later tickets
which do add a frontend env var have the pattern already in place — no real values are ever committed.

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ESLint flat-config vs. legacy `.eslintrc.cjs` ambiguity depending on the ESLint major version Vite's scaffold pulls in | Medium | Low | Resolve at implementation time by checking the installed ESLint version; either config style satisfies base-rules.md's rule-set requirement — pick one and keep it consistent, documented in the PR. |
| Vitest/jsdom/RTL config mismatch with `tsconfig.json`'s `types` array (a common Vite+Vitest setup failure) | Medium | Medium | Task 5 is isolated and independently validated (`npm run test` exit code) before moving to Task 6, so a config error is caught and fixed before layering Docker/final-integration on top. |
| Docker build step slows local iteration if run after every task | Low | Low | Docker build validation is deferred to Task 6/7 rather than run after every task. |
| Empty domain folders (`chat/`, `dashboard/`, `shared/`, `api/`) are not git-tracked without a placeholder file | High (certain without mitigation) | Low | Task 3 explicitly adds a `.gitkeep`/`README.md` placeholder per folder. |

---

## Estimated Complexity

| Task | Complexity |
|---|---|
| Task 1 — Vite + React + TS scaffold | `Low` |
| Task 2 — tsconfig strict mode | `Low` |
| Task 3 — src/ domain skeleton | `Low` |
| Task 4 — ESLint + Prettier | `Low` |
| Task 5 — Vitest + RTL wiring | `Medium` |
| Task 6 — Dockerfile | `Low` |
| Task 7 — Final integration check | `Low` |
| **Overall** | `Low` |

---

## Out of Scope

- **No real feature UI.** `chat/`, `dashboard/`, `shared/`, `api/` are created as empty skeleton folders
  only — no Web Chat widget, no Owner Dashboard, no shared component library, and no typed API client
  implementation. Those are separate, later frontend-facing stories.
- **No backend integration.** `B2B_BE/` does not exist yet; no HTTP client, WebSocket connection, or API
  contract is implemented against it. `src/api/` remains an empty placeholder.
- **No `docker-compose.yml` changes.** The root orchestration file (backend + frontend + Postgres) is a
  separate, cross-cutting concern per `stack-proposal.md` §5 and is not touched by this ticket — only
  `B2B_FE/Dockerfile` (a standalone, independently buildable image) is in scope.
- **No CI/CD pipeline wiring.** No GitHub Actions workflow is added or modified for this ticket, beyond
  what already exists (e.g. `scope-check.yml`, unrelated to this ticket). base-rules.md notes CI/CD as
  optional and not required by any FR.
- **No deployment.** Hosting (local+tunnel or PaaS, per `stack-proposal.md` §5) is not addressed here.
- **No auth, routing, or state-management library.** None is required to render a trivial placeholder
  page; introducing one speculatively (e.g. React Router, Redux/Zustand) is scope creep against this
  ticket's AC and is deferred to whichever later story first needs it.
- **No B2B_BE/ changes of any kind**, per `CLAUDE.md`'s Repository layout rule — this is a frontend-only
  ticket.

---

*Generated by sdlc-dev-workflow · Ticket: `APPOINTMEN-10` · Branch:
`feature/APPOINTMEN-10-02-frontend-project-scaffolding`*
