# QA Feature Summary — APPOINTMEN-10: Frontend project scaffolding

> Phase 1 (Feature Understanding) output, sdlc-qa-workflow. Written by Test Agent.

## Ticket

Jira `APPOINTMEN-10` (Story, label: frontend, status: In QA) — "0.2 Frontend project scaffolding."
PR: https://github.com/cache-mee/PRISMArc/pull/13, branch
`feature/APPOINTMEN-10-02-frontend-project-scaffolding` → `develop`.

## What the feature does

Initializes `B2B_FE/` from nothing into a working Vite + React 18+/TypeScript 5+ scaffold, so that later
frontend-facing stories (Web Chat widget, Owner Dashboard) have a running app to build against. It is
purely developer-facing plumbing: there is no end-user-visible functionality beyond a trivial placeholder
page rendered by the dev server. Concretely it delivers:

- `package.json` with React/TypeScript/Vite (all well above the "18+/5+/5+" floors — actual installed
  versions are React 19.3.0, TypeScript 6.0.3, Vite 8.3.0, ESLint 10.10.0).
- `tsconfig.json` / `tsconfig.app.json` / `tsconfig.node.json` with `"strict": true`.
- `src/App.tsx`, `src/main.tsx`, `index.html` — the placeholder page and its mount path.
- `src/{chat,dashboard,shared,api}/.gitkeep` — the four required empty domain-folder skeletons.
- `eslint.config.js` (flat config) + `.prettierrc` + `.prettierignore` — lint/format tooling.
- `tests/setup.ts` + `tests/App.test.tsx` — Vitest + React Testing Library wired, one smoke test.
- `Dockerfile` (multi-stage: `node:22-alpine` build → `nginx:alpine` runtime) + `.dockerignore` +
  `nginx.conf` (SPA fallback, needed by the Dockerfile's runtime stage, undocumented in the plan but
  correctly scoped).
- `public/favicon.svg` (referenced by `index.html`, undocumented in the plan but trivial/in-scope).
- `.gitignore`, `package-lock.json`.

Not delivered: `.env.example` (named in the plan's Affected Areas table, missing from the diff — a
documented MINOR gap in the dev review, no functional impact since no frontend env var exists yet).

## Components that interact

This is a pure frontend scaffolding ticket. Being direct about what does and does not exist:

- **No `B2B_BE/`** — the backend folder does not exist anywhere in this repository yet.
- **No database** — no Postgres, no schema, no migration touches this ticket.
- **No API calls** — `src/api/` is an empty placeholder folder (`.gitkeep` only); no HTTP client, no
  fetch/axios usage, no typed client implementation.
- **No cross-service interaction** — nothing in this PR talks to anything outside the `B2B_FE/` build
  pipeline itself.

The only "interactions" present are internal to the frontend toolchain: Vite's dev/build pipeline reading
`tsconfig`/`vite.config.ts`, ESLint/Prettier running against the scaffolded source, Vitest+RTL rendering
`App.tsx` in jsdom, and the Dockerfile's build stage invoking `npm ci && npm run build` before handing
`dist/` to an nginx runtime stage. All of these are single-component, tool-against-its-own-config
relationships, not two independently-owned application components talking to each other.

## Acceptance criteria (verbatim, decomposed for 1:1 test-scenario mapping in Phase 2)

| # | Criterion | Source evidence in repo |
|---|---|---|
| AC1 | `package.json` present with React 18+, TypeScript 5+, Vite 5+ | `B2B_FE/package.json` — react `^19.2.8`/installed `19.3.0`, typescript `~6.0.2`/installed `6.0.3`, vite `^8.3.0` |
| AC2 | Dockerfile builds the app | `B2B_FE/Dockerfile` (multi-stage), `.dockerignore`, `nginx.conf` — **dev-review notes `docker build` was never executed in that review sandbox (Docker not installed there); content-inspected only** |
| AC3 | `tsconfig` has `strict: true` | `B2B_FE/tsconfig.app.json`, `tsconfig.node.json` — confirmed by direct file read in dev review |
| AC4 | `src/` skeleton: `chat/`, `dashboard/`, `shared/`, `api/` | `B2B_FE/src/{chat,dashboard,shared,api}/.gitkeep` all present |
| AC5 | ESLint + Prettier configured | `B2B_FE/eslint.config.js`, `.prettierrc`, `.prettierignore` — dev review re-ran `npm run lint` and `npm run format:check`, both exit 0 |
| AC6 | `tests/` skeleton, Vitest+RTL path wired | `B2B_FE/tests/setup.ts`, `tests/App.test.tsx` — dev review re-ran `npm run test`, exit 0, 1/1 passing |
| AC7 | Dev server renders a trivial placeholder page in a browser | `src/App.tsx`/`src/main.tsx`/`index.html` content-inspected as a correct, unbroken render path — **no automated command proves this; dev-review explicitly flags this as never independently verified in an actual browser (no browser available in that review sandbox)** |

Two acceptance criteria (AC2 Dockerfile-builds-the-app, AC7 dev-server-renders-in-browser) have **known
verification gaps carried forward from the dev review**: they were reasoned about via file inspection, not
executed, because Docker and a browser were unavailable in that sandbox. Phase 2/3 of this QA workflow
should treat these as the two highest-priority scenarios to actually execute end-to-end, since they are
the only two ACs without a recorded exit code.

## Integration-boundary assessment

**No real integration-test boundary exists yet for this ticket.** An "integration test" implies two or
more real, independently-owned components exchanging data at a boundary — e.g. a service talking to a
database, or a frontend client talking to a live backend API. Neither exists here:

- `B2B_BE/` is not present in the repository at all — there is nothing for `src/api/` to call.
- There is no database, no persisted state, no network boundary of any kind introduced by this PR.
- The four `src/` domain folders (`chat/`, `dashboard/`, `shared/`, `api/`) are empty directories holding
  only a `.gitkeep` file — no code exists inside them to integrate with anything, including each other.

What this ticket actually wires is **build-pipeline/tooling configuration**: Vite's dev/build pipeline,
TypeScript's strict compiler, ESLint/Prettier, Vitest+RTL's test runner, and a Docker multi-stage build.
These are legitimate things to validate (and Phase 2 should map each AC above to a concrete
command-with-exit-code check), but they are configuration/build-pipeline checks, not component-to-component
integration tests. Forcing an "integration test" onto this ticket would mean fabricating a boundary that
does not exist in the codebase — e.g., mocking a non-existent backend just to claim an integration test
ran. Phase 2 test planning should scope this ticket to: one unit/component-level check per AC (build exits
0, typecheck exits 0, lint/format exit 0, test suite exits 0 with the smoke test passing, Docker image
builds and exits 0, dev server starts and serves content confirmed via a real browser or headless-browser
check for AC7) — and explicitly record "no integration test applicable" rather than inventing one.

The first ticket where a genuine integration boundary will exist is whichever story first wires `B2B_FE/`
to a real `B2B_BE/` endpoint — not this one.
