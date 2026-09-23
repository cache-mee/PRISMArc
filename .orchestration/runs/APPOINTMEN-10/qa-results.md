## QA Test Results — APPOINTMEN-10

Run at: 2026-09-17T10:43:30+00:00
Branch: feature/APPOINTMEN-10-02-frontend-project-scaffolding

| Test case | AC | Status | Command | Exit code | Notes |
|---|---|---|---|---|---|
| TC1.1 | AC1 | PASS | Read `B2B_FE/package.json` (manual inspection) | n/a | `react: ^19.2.8`, `typescript: ~6.0.2`, `vite: ^8.3.0` — all floors (react≥18, ts≥5, vite≥5) met |
| TC1.2 | AC1 | PASS | `npm ci` then `npm ls react typescript vite --depth=0` (from `B2B_FE/`) | 0 | Installed: `react@19.3.0`, `typescript@6.0.3`, `vite@8.3.0` — all meet floors, no lockfile drift below floor. `npm ci` itself also exited 0 (235 packages, engine warnings only — installed Node v25.9.0 vs some devDeps wanting ^22/^24/26, non-fatal) |
| TC1.3 | AC1 | PASS | `rm -rf dist && npm run build` (from `B2B_FE/`) | 0 | `tsc -b && vite build` completed; `dist/` produced (`index.html`, JS/CSS assets), no TS/Vite version-incompatibility errors |
| TC2.1 | AC2 | NOT VALIDATED | `docker build -t b2b-fe-qa:appointmen-10 -f B2B_FE/Dockerfile B2B_FE` (from repo root) | 127 | `docker: command not found` — Docker Engine not installed/invocable on this machine, confirmed same as plan-time finding |
| TC2.2 | AC2 | NOT VALIDATED | (blocked — no image built to run) | n/a | Cannot execute; depends on TC2.1 producing an image |
| TC2.3 | AC2 | PASS | Same command as TC2.1, observing failure mode | 127 | Fallback procedure worked as designed: attempted the real build, `docker` failed to invoke at all (exit 127, "command not found"), result honestly recorded as NOT VALIDATED rather than skipped or faked. Docker availability gap stands and is escalated below |
| TC3.1 | AC3 | PASS | `grep -n '"strict"' tsconfig.app.json tsconfig.node.json` (from `B2B_FE/`) | 0 | Both files declare `"strict": true` (`tsconfig.app.json:20`, `tsconfig.node.json:17`) |
| TC3.2 | AC3 | PASS | `npm run build` (from `B2B_FE/`) — same run as TC1.3 | 0 | `tsc -b` reported no strict-mode violations |
| TC4.1 | AC4 | PASS | `ls B2B_FE/src/` | 0 | `chat/`, `dashboard/`, `shared/`, `api/` all present as directories alongside `App.tsx`, `main.tsx`, `index.css` |
| TC4.2 | AC4 | PASS | `git ls-files B2B_FE/src/chat B2B_FE/src/dashboard B2B_FE/src/shared B2B_FE/src/api` | 0 | Returned `src/api/.gitkeep`, `src/chat/.gitkeep`, `src/dashboard/.gitkeep`, `src/shared/.gitkeep` — all four folders tracked by git |
| TC5.1 | AC5 | PASS | `npm run lint` (from `B2B_FE/`) | 0 | `eslint .` — no lint errors reported |
| TC5.2 | AC5 | PASS | `npm run format:check` (from `B2B_FE/`) | 0 | `prettier --check .` — "All matched files use Prettier code style!" |
| TC6.1 | AC6 | PASS | `npm run test` (from `B2B_FE/`) | 0 | `vitest run` — 1 test file, 1 test passed, 0 failures |
| TC6.2 | AC6 | PASS | Read `B2B_FE/tests/App.test.tsx` (manual inspection) | n/a | Imports `@testing-library/react`, renders `<App />`, asserts `screen.getByRole("heading", { name: "Salon App" })` — real assertion on rendered DOM content, not a trivial stub |
| TC7.1 | AC7 | PASS | `npm run dev` (background, from `B2B_FE/`) | 0 (server process) | Log: `VITE v8.3.0 ready in 255 ms`, `Local: http://localhost:5173/` — no startup error |
| TC7.2 | AC7 | PASS | `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` | 0 | HTTP 200 |
| TC7.3 | AC7 | PASS | `"chrome.exe" --headless=new --disable-gpu --dump-dom http://localhost:5173/ > dev-dump.html` then `grep -o "<h1>Salon App</h1>" dev-dump.html` | 0 | Chrome found at `C:\Program Files\Google\Chrome\Application\chrome.exe`. Dumped DOM contains `<h1>Salon App</h1>` inside the executed page — confirms React actually mounted (source text verified in `B2B_FE/src/App.tsx`) |
| TC7.4 | AC7 | PASS | `npm run build` (see TC1.3) then `npm run preview` (background), then same headless-Chrome dump-dom against `http://localhost:4173/` | 0 | Preview log: `Local: http://localhost:4173/`. Dumped DOM contains `<h1>Salon App</h1>` — production build also renders correctly |
| TC7.5 | AC7 | PASS | `taskkill //PID <dev-pid> //F` and `taskkill //PID <preview-pid> //F` (Windows PIDs from `netstat -ano`, not the MSYS-translated PIDs from `ps`), then re-curled both ports | 0 (both taskkill calls) | Both processes terminated ("SUCCESS" from taskkill); post-kill `curl` to :5173 and :4173 returned exit 7 (connection refused) and `netstat -ano` showed no LISTENING entries on either port — ports cleanly released |

Summary:
  Total:      19
  Passed:     17
  Failed:     0
  Not validated: 2 (TC2.1, TC2.2 — Docker unavailable on this machine)

## Environment gaps (escalated, not silently accepted)

- **Docker**: still absent/not invocable on this QA machine (`docker` → exit 127, command not found). This is the second QA pass in a row (dev review + this session) unable to produce a real `docker build` exit code for AC2. TC2.1/TC2.2 remain **not validated**, not passed. AC2 (Dockerfile builds the app) has never been mechanically proven on any machine used in this ticket's lifecycle — this should be flagged to the Lead/human gate as an outstanding risk before AC2 is considered done, e.g. by running the same `docker build` command in CI or on a machine with Docker Desktop installed.
- **Headless browser**: by contrast, this gap from the test plan's preamble was successfully closed in this session — both Chrome and Edge binaries were located and Chrome was used to produce real TC7.3/TC7.4 evidence. No browser-side gap remains for AC7.
