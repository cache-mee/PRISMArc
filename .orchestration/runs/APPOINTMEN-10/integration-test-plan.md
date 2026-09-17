# Integration Test Plan — APPOINTMEN-10: Frontend project scaffolding

> Phase 2 (Integration Test Plan) output, sdlc-qa-workflow. Written by Test Agent.
> Planning only — nothing in this document has been executed yet. Execution is
> gated by human approval (Phase 3).

## Preamble — why this plan contains no integration tests

Phase 1 (`qa-feature-summary.md`) established that **no genuine integration-test
boundary exists yet for this ticket**, and that conclusion is carried forward
unchanged here. An integration test implies two or more real, independently-owned
components exchanging data at a boundary — a service talking to a database, or a
frontend client talking to a live backend API. Neither exists in this PR:
`B2B_BE/` is not present anywhere in the repository, there is no database or
network boundary introduced, and the four `src/` domain folders
(`chat/`, `dashboard/`, `shared/`, `api/`) hold only `.gitkeep` placeholders with
no code to integrate with anything, including each other. What this ticket wires
is exclusively single-component, tool-against-its-own-config plumbing (Vite,
TypeScript, ESLint/Prettier, Vitest+RTL, Docker). Fabricating an "integration
test" here — e.g. mocking a non-existent backend just to produce one — would
manufacture a boundary that does not exist and would violate the qa-workflow's
own rule against inventing test boundaries. Accordingly, every check below is
typed **Build/Config verification** rather than Integration, and there is a 1:1
mapping from AC to check, executed for real in this QA session rather than
re-trusted from the dev review's claims.

Two checks (AC2, AC7) are the priority items: the dev review recorded no exit
code for either (Docker was unavailable in that sandbox for AC2; no browser was
available there for AC7). Before finalizing this plan, environment
reconnaissance was run in this QA session to avoid proposing tooling that isn't
actually present:

- **Docker**: not found (`docker` absent from PATH; no Docker Desktop install
  directory present on this machine either). This QA session cannot execute a
  real `docker build` any more than the dev-review sandbox could. Phase 3 MUST
  attempt the check anyway and record the true outcome — if Docker is still
  unavailable, the honest result is **not validated**, not a pass.
- **Browser automation frameworks** (Playwright, Puppeteer, Cypress): none are
  installed in `B2B_FE/package.json` (only `jsdom`, used by Vitest for
  component-level rendering, not a full browser). No new framework is proposed
  to be installed as part of this QA pass, per the ticket's instruction not to
  introduce tooling absent from the repo.
- **Real browsers**: Google Chrome and Microsoft Edge are both installed on
  this machine (`chrome.exe`, `msedge.exe` present under
  `C:\Program Files...\Application\`). Both support a scripted headless mode
  (`--headless=new --dump-dom <url>`) that actually executes the page's JS
  (React mount) and returns the final DOM — unlike `curl`, which would only
  return the static `index.html` shell before `main.tsx` runs and therefore
  cannot prove the placeholder text renders. AC7's check uses this real-browser
  headless mode rather than a plain HTTP fetch.

## AC1 — `package.json` has React 18+, TypeScript 5+, Vite 5+

### Components under test
`B2B_FE/package.json` dependency/devDependency declarations and the installed
`node_modules` tree they resolve to.

### Test environment
Repo root checkout of `feature/APPOINTMEN-10-02-frontend-project-scaffolding`,
`B2B_FE/` with `npm ci` already run (or run fresh in this session), this QA
session's shell.

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| TC1.1 — declared version floors met | Fresh checkout of the PR branch, `cd B2B_FE` | Read `package.json`; parse `react`, `typescript`, `vite` version ranges | `react` ≥ 18, `typescript` ≥ 5, `vite` ≥ 5 (all present and satisfy the floor) | Build/Config verification |
| TC1.2 — installed versions match | `npm ci` completed | Run `npm ls react typescript vite --depth=0` | Command exits 0; resolved versions each meet the same floors (no lockfile drift below the required floor) | Build/Config verification |
| TC1.3 — project actually builds against these versions | `npm ci` completed | Run `npm run build` from `B2B_FE/` | Exit code 0; `dist/` produced with no TypeScript/Vite version-incompatibility errors | Build/Config verification |

## AC2 — Dockerfile builds the app

### Components under test
`B2B_FE/Dockerfile`, `.dockerignore`, `nginx.conf` — the multi-stage
`node:22-alpine` build → `nginx:alpine` runtime image.

### Test environment
Repo root, this QA session's machine, Docker Engine if available (**confirmed
absent from this machine at plan time** — see Preamble).

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| TC2.1 — image builds | Fresh checkout of the PR branch, Docker Engine reachable | From repo root run `docker build -t b2b-fe-qa:appointmen-10 -f B2B_FE/Dockerfile B2B_FE` | Exit code 0; final image tagged successfully; no build-stage failure | Build/Config verification |
| TC2.2 — image serves content | TC2.1 image built | `docker run --rm -d -p 8080:80 b2b-fe-qa:appointmen-10`, then `curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/` | HTTP 200 returned; container logs show nginx serving `dist/` (SPA fallback per `nginx.conf`) | Build/Config verification |
| TC2.3 — environment gap (fallback) | Docker not installed/reachable in this session | Attempt TC2.1; on failure to invoke `docker` at all | Record result as **not validated** (not pass, not fail) with the exact error, and escalate the Docker-availability gap rather than silently skipping AC2 | Build/Config verification |

## AC3 — `tsconfig` strict mode

### Components under test
`B2B_FE/tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`.

### Test environment
Repo root checkout, this QA session's shell, Node/npm as declared in
`package.json` engines (if any) / installed locally.

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| TC3.1 — strict flag present | Fresh checkout | Read `tsconfig.app.json` and `tsconfig.node.json`; grep for `"strict"` | Both files declare `"strict": true` | Build/Config verification |
| TC3.2 — strict mode actually enforced | `npm ci` completed | Run `npm run build` (invokes `tsc -b && vite build`) from `B2B_FE/` | Exit code 0; `tsc -b` reports no strict-mode violations | Build/Config verification |

## AC4 — `src/` domain skeleton

### Components under test
`B2B_FE/src/chat/`, `src/dashboard/`, `src/shared/`, `src/api/`.

### Test environment
Repo root checkout, filesystem listing only (no build required).

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| TC4.1 — all four folders exist | Fresh checkout | List `B2B_FE/src/` | `chat/`, `dashboard/`, `shared/`, `api/` all present as directories | Build/Config verification |
| TC4.2 — folders are tracked by git (not local-only) | Fresh checkout | Run `git ls-files B2B_FE/src/chat B2B_FE/src/dashboard B2B_FE/src/shared B2B_FE/src/api` | Each folder returns at least one tracked file (`.gitkeep`), confirming the skeleton is committed, not an artifact of this session | Build/Config verification |

## AC5 — ESLint + Prettier configured

### Components under test
`B2B_FE/eslint.config.js`, `.prettierrc`, `.prettierignore`.

### Test environment
Repo root checkout, `npm ci` completed, this QA session's shell.

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| TC5.1 — lint passes clean | `npm ci` completed | Run `npm run lint` from `B2B_FE/` | Exit code 0, no lint errors reported | Build/Config verification |
| TC5.2 — formatting passes clean | `npm ci` completed | Run `npm run format:check` from `B2B_FE/` | Exit code 0, no files flagged as unformatted | Build/Config verification |

## AC6 — `tests/` skeleton, Vitest + RTL wired

### Components under test
`B2B_FE/tests/setup.ts`, `tests/App.test.tsx`, `vite.config.ts` test block.

### Test environment
Repo root checkout, `npm ci` completed, this QA session's shell (jsdom
environment, no real browser needed for this AC — it is a unit/component test
runner check, not the AC7 browser-render check).

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| TC6.1 — test suite runs and passes | `npm ci` completed | Run `npm run test` (`vitest run`) from `B2B_FE/` | Exit code 0; 1 test file, 1 test passing (the `App.test.tsx` smoke test), 0 failures | Build/Config verification |
| TC6.2 — RTL actually wired, not a stub | `npm ci` completed | Read `tests/App.test.tsx`; confirm it imports `@testing-library/react`, renders `<App />`, and asserts on rendered output (not a trivial `expect(true).toBe(true)`) | Assertion targets real rendered DOM content (e.g. the `Salon App` heading) | Build/Config verification |

## AC7 — Dev server renders a trivial placeholder page in a browser

### Components under test
`B2B_FE/index.html`, `src/main.tsx`, `src/App.tsx`, served via `vite` dev
server (or `vite preview` against a production build).

### Test environment
Repo root checkout, `npm ci` completed, this QA session's shell, a real
installed browser in headless mode (Chrome or Edge — both confirmed present on
this machine; no Playwright/Puppeteer/Cypress install required or proposed).

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| TC7.1 — dev server starts | `npm ci` completed | Run `npm run dev` from `B2B_FE/`, wait for the "ready" log line | Process starts, prints a local URL (default `http://localhost:5173/`), no startup error | Build/Config verification |
| TC7.2 — server responds | TC7.1 server running | `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` | HTTP 200 (confirms the static shell is served; does not by itself prove React mounted, since the placeholder text is client-rendered by `main.tsx`) | Build/Config verification |
| TC7.3 — placeholder actually renders in a browser | TC7.1 server running | Run headless Chrome (or Edge) against the dev URL and capture the executed DOM, e.g. `chrome.exe --headless=new --disable-gpu --dump-dom http://localhost:5173/ > dump.html`, then grep the dump for the placeholder text | Dumped DOM contains `<h1>Salon App</h1>` (or equivalent rendered placeholder text) inside `#root` — proving React actually mounted in a real browser engine, not just that the static shell was served | Build/Config verification |
| TC7.4 — production build also renders (belt-and-suspenders) | `npm run build` completed | `npm run preview`, repeat TC7.3 against the preview URL (default `http://localhost:4173/`) | Same placeholder text present in the dumped DOM, confirming the built artifact (not just the dev server) renders correctly | Build/Config verification |
| TC7.5 — kill server | Any dev/preview server left running from TC7.1–TC7.4 | Terminate the `npm run dev` / `npm run preview` process | Process exits cleanly, port released | Build/Config verification |

## Coverage summary

| AC | Check IDs | Priority (per Phase 1) |
|---|---|---|
| AC1 | TC1.1–TC1.3 | Normal — dev review already re-ran build |
| AC2 | TC2.1–TC2.3 | **High — no recorded exit code before this QA pass; Docker confirmed absent on this machine at plan time, must attempt and honestly record outcome** |
| AC3 | TC3.1–TC3.2 | Normal |
| AC4 | TC4.1–TC4.2 | Normal |
| AC5 | TC5.1–TC5.2 | Normal — dev review already re-ran lint/format |
| AC6 | TC6.1–TC6.2 | Normal — dev review already re-ran test suite |
| AC7 | TC7.1–TC7.5 | **High — no recorded exit code before this QA pass; real-browser headless-dump approach chosen since no automation framework is installed** |

Seven acceptance criteria, seven check groups, one-to-one. No integration test
is included, per the Preamble justification above. Execution (Phase 3) will
run each command in this QA session and record command, scope, exit code, and
artifact path per `.orchestration/schemas/evidence.md` — nothing above has been
executed yet.
