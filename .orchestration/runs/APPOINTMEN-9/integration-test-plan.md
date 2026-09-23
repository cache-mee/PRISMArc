# Integration Test Plan — APPOINTMEN-9

## Work ID
APPOINTMEN-9

## Last Updated
2026-09-17T10:42:22+00:00

## Overall assessment (read this before the per-AC tables)

Per the skill's own boundary rule: *"Integration tests verify that two or more real components work
correctly together. They are not unit tests and they are not E2E UI tests."* Per `stack/rules/
base-rules.md` (Testing Requirements), this project's own definition of an integration-style test is
"hitting a real Postgres via `docker-compose`, not a mocked DB" — reserved for FR-9, FR-18, FR-26/FR-27
(confirm-before-write and conflict detection), none of which exist yet.

Having read every changed file (see `qa-feature-summary.md`), this ticket is pure scaffolding per its own
approved plan's "Out of Scope" section: no DB engine, no repository/domain/agent/tool logic, no second
internal service, no external API. There is genuinely **no second real component** for AC1, AC3, AC4, or
AC5 to integration-test against. Forcing an "integration test" onto any of them would just be
`tests/test_health.py` (already present) relabelled — an in-process `TestClient` call is a single-process
unit/route test by the skill's own table ("Unit test of a single function" / mocking-everything row), not
an integration test, regardless of what it's named.

**One candidate genuine boundary exists: AC2 (Dockerfile builds the service), extended to "the built
container serves `/health` over a real network socket."** That crosses a real boundary this ticket
actually introduces — the packaged-artifact boundary (source → installed dependencies → container
runtime → `uvicorn` process → real TCP socket) — which is categorically more than the in-process
`TestClient` unit test already covers. It is not mocked: real `docker build`, a real running container, a
real HTTP client making a real request to a real port.

**This candidate cannot be executed in the current environment.** Verified directly: `docker --version` →
`command not found`. Per the Developer/Test agent evidence rules, an unrunnable check is reported as *not
validated*, never faked as pass. It is included below as a planned, honest check — to be executed if/when
Docker is available (Task 5 of the approved plan already treats the container smoke-run as
"optional... time-permitting... if Docker is unavailable, reported as not validated").

**Recommendation: defer integration testing for AC1, AC3, AC4, AC5, AC6 in isolation — they have no
component boundary to test yet — and treat AC2 as the one candidate integration-style check, contingent
on Docker availability.** The first ticket that wires a real second component (a live Postgres connection
via SQLAlchemy + repository code, or a real external API/webhook) is where a conventional integration
test suite (real service layer ↔ real DB) becomes possible and required. This is consistent with the
approved implementation plan's own Testing Strategy table: *"Integration — Not applicable — no DB, agent,
or external integration exists yet to integration-test in this ticket."*

No padding: the count of genuine integration test cases planned in this document is **1** (Docker/network
boundary check for AC2), and it is currently blocked/not-executable pending Docker availability. All
other ACs are marked "no integration boundary — deferred" below, each with the reason, rather than filled
with disguised unit-test duplicates.

---

### AC1: `pyproject.toml` (Python 3.12+, deps: fastapi, uvicorn, sqlalchemy, alembic, pydantic v2, pytest)

**Components under test:** None — single manifest file, no runtime component to pair it with.
**Test environment:** N/A.

No integration test proposed. A dependency manifest resolving/installing correctly is a build-validation
concern (`pip install .` exit code), not a boundary between two real components. Structural correctness
is already verifiable by inspection (done in Phase 1) and by the existing pytest run succeeding using this
manifest's config (see AC5/AC6). Deferred — no boundary exists.

---

### AC2: Dockerfile builds the service

**Components under test:** Packaged container image (real `uvicorn` process, real Python 3.12 runtime,
real installed dependency set) ↔ a real HTTP client over a real TCP socket.
**Test environment:** Real — `docker build` against the actual `B2B_BE/Dockerfile`, a real running
container, a real network request from the host to the container's exposed port. Nothing mocked. No
external service is involved (LLM, Twilio, Postgres) so no third-party mocking question arises.

| Test case | Setup | Action | Expected result | Type |
|---|---|---|---|---|
| Happy path: container builds and serves `/health` | `docker build -t b2b-be:scaffold B2B_BE/` from repo root | Run the built image (`docker run -p 8000:8000 b2b-be:scaffold`), then `curl http://localhost:8000/health` (or an `httpx` request) from the host | Build exits 0; container starts; HTTP response is `200` with body `{"status": "ok"}` | Integration |

**Status: BLOCKED — not executable in this environment.** `docker --version` returns `command not found`
here. This test case is planned and will be run and its evidence recorded as soon as Docker is available
(locally or in CI); until then it MUST be reported as **not validated**, not as pass, per the evidence
schema. If Docker remains unavailable for this QA pass entirely, AC2 is validated only by inspection (the
Dockerfile content is structurally correct — `FROM python:3.12-slim`, installs `pyproject.toml`, copies
`app/`, runs `uvicorn app.main:app`) which is a judgement-type record, not a deterministic pass.

---

### AC3: `app/main.py` + `app/config.py` (env-var secrets, `.env.example`)

**Components under test:** None available yet. `app/main.py` importing `settings` from `app/config.py`
is a same-process, same-deploy-unit Python import — not two components crossing a boundary (no network
hop, no persistence, no separate deployable). `database_url` is declared but no engine/session is ever
constructed from it anywhere in this diff, so there is no DB component to pair it with either.
**Test environment:** N/A — no second component exists to integration-test.

No integration test proposed. Deferred to the first ticket that actually constructs a SQLAlchemy engine
from `database_url` and connects to a real Postgres instance — at that point "config → real DB
connection" becomes a genuine, testable boundary.

---

### AC4: Full package skeleton per stack-proposal.md §9 (api/, agent/, tools/, domain/, models/,
repositories/)

**Components under test:** None — every package under `app/` in this diff contains only an empty
`__init__.py`. There is no logic in any of them to pair with anything.
**Test environment:** N/A.

No integration test proposed. Importability of empty packages is a structural/collection check (already
implicitly exercised by `pytest`'s test collection succeeding without import errors) — not an integration
test by any reading of the skill's boundary table. Deferred until each package gains real logic that
actually calls into another real component (e.g. `app/repositories/` talking to a real DB session,
`app/tools/` calling into `app/domain/` which writes through a real repository).

---

### AC5: `tests/` skeleton runnable via pytest

**Components under test:** None — this AC is the test infrastructure itself (the thing that runs the
tests), not a feature with a component boundary to verify.
**Test environment:** N/A.

No integration test proposed. Confirmed instead as a build/tooling fact: `pytest` collects and runs from
`B2B_BE/` per `pyproject.toml`'s `testpaths = ["tests"]`. This is evidence to capture at execution time
(Phase 3 would capture it if there were tests to run), not something to integration-test in itself.

---

### AC6: `GET /health` returns 200 when run

**Components under test:** In isolation, none beyond FastAPI's own in-process routing — already fully
covered by the existing `tests/test_health.py` unit/route test (FastAPI `TestClient`, in-process, no
socket, no second component). Per the skill's own table this is explicitly **not** an integration test
("Unit test of a single function" / API endpoint via in-process test client without a real second
component is the unit-test row, not the integration row).
**Test environment:** N/A for a distinct integration test — would only duplicate `test_health.py` with a
different label.

No additional integration test proposed for AC6 standing alone — writing one would just be
`test_health.py` copy-pasted with a new file name, which the Test agent must not do (padding a plan with
tests that are not genuinely integration tests just to hit a count). AC6 is, however, folded into the AC2
container-boundary check above: hitting `GET /health` over a real socket against the built container *is*
the meaningful, non-duplicate way to test this criterion at an integration level, because it adds the
real boundary (packaging + real process + real network) that the existing unit test does not cross.

---

## Summary

| Metric | Count |
|---|---|
| Acceptance criteria total | 6 |
| Acceptance criteria with a genuine integration-test boundary | 1 (AC2, extended to also cover AC6 over that boundary) |
| Acceptance criteria explicitly deferred (no boundary exists yet) | 5 (AC1, AC3, AC4, AC5, AC6-standing-alone) |
| Integration test cases planned | 1 |
| Integration test cases currently executable in this environment | 0 (Docker unavailable — reported as not validated, not as pass) |

## Recommendation to present at Gate 2

Approve this plan as-is with the deferral explicitly acknowledged, OR direct that the single AC2
container-boundary case be attempted anyway (would still be blocked by Docker's absence here and would
need to run in an environment with Docker, e.g. CI), OR explicitly waive integration testing for this
ticket entirely and record that decision, given the ticket is scaffolding with no real second component.
No fabricated integration tests will be added regardless of which option is chosen.
