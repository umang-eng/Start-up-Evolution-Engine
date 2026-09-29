# Platform Testing Report

**Test date:** 2026-09-29  
**Environment:** macOS, Node 25.6.0, npm 11.8.0, Python 3.13.5  
**Application:** Start-up Evolution Engine  
**Verdict:** **Conditionally ready for local UI/API development; not production-ready**

## Executive summary

The frontend compiles and lints without errors, the backend test suite passes, and the core local services (FastAPI, SQLite fallback, Redis, and Ollama) are reachable. Authentication, project creation, project listing, health checks, and generator request acceptance were verified through authenticated API smoke tests.

The complete real 14-stage AI pipeline is not yet verified as successful. A first end-to-end run failed at the `features` stage because the orchestrator reused an SQLAlchemy identity-mapped `Project` and did not reload the newly persisted DNA relationship. That defect was fixed by enabling `populate_existing=True` on orchestrator reload queries, and the focused orchestrator tests still pass. A second real run progressed through DNA and features to `roadmap`, but remained `RUNNING` during the test window while waiting on Ollama generation. No completed blueprint was available at the end of the test window.

## Test matrix

| Area | Test | Result | Evidence / notes |
|---|---|---:|---|
| Frontend | `npm run lint` | PASS | 0 errors, 80 existing warnings |
| Frontend | `npm run build` | PASS | Next.js 16.3.6 production build completed |
| Frontend | `/`, `/login`, `/signup`, `/meetings`, `/forgot-password`, `/reset-password` | PASS | HTTP 200 route smoke checks |
| Backend | `PYTHONPATH=. backend/venv/bin/pytest backend/tests -q` | PASS | 18 passed, 1 deprecation warning |
| Backend | Orchestrator tests | PASS | 10 passed after relationship-refresh fix |
| API | Liveness | PASS | `status=healthy` |
| API | Readiness | PASS | Database and Redis reported `UP` |
| API | Register/login/profile | PASS | Authenticated smoke flow succeeded |
| API | Project creation/listing | PASS | Correct `title`, `description`, and `industry` contract verified |
| API | Generator request | PASS | Request accepted and ARQ session returned |
| Pipeline | First real 14-stage run | FAIL | Stopped at `features`; missing DNA context |
| Pipeline | Second real run after fix | BLOCKED | Reached `roadmap`, remained running during observation window |
| Blueprint persistence | Retrieve completed blueprint | BLOCKED | No completed blueprint from the observed run |
| Ollama | `/api/tags` and generation availability | PASS | Local `gemma2:2b` service reachable |
| Redis | PING and ARQ connectivity | PASS | Redis returned `PONG`; worker active |
| Puter.js | CDN availability | PASS | CDN returned HTTP 200 |
| Puter transcription | Real browser authorization and speech transcription | NOT EXECUTED | Requires interactive browser and Puter sign-in |
| Meeting recording/replay/report UI | Browser workflow | NOT EXECUTED | Requires interactive browser/media permissions |
| PostgreSQL | Production database behavior | BLOCKED | PostgreSQL was not running; SQLite fallback used |
| Whisper-compatible service | Port 9000 transcription fallback | BLOCKED | Service was not running |
| Search/evidence integrations | Tavily/Google-backed stages | BLOCKED | Credentials are not configured |
| Docker deployment | Containerized stack | BLOCKED | Docker unavailable in the test environment |

## Commands executed

```text
npm run lint
npm run build
PYTHONPATH=. backend/venv/bin/pytest backend/tests -q
PYTHONPATH=. backend/venv/bin/pytest backend/tests/test_orchestrator.py -q
curl http://127.0.0.1:8000/api/v1/health/liveness
curl http://127.0.0.1:8000/api/v1/health/readiness
```

An authenticated API script also registered a test user, logged in, created a project, triggered generation, polled the project/session state, and attempted blueprint retrieval.

## Defects found and status

### Fixed during this test

1. **Pipeline context reload defect:** after DNA persisted, the next stage received an empty DNA context because SQLAlchemy reused the existing identity-mapped project. Orchestrator reloads now use `populate_existing=True`.
2. **API/worker SQLite path mismatch:** API and ARQ worker could resolve the fallback database relative to different working directories. The fallback path is now absolute and derived from the backend package location.
3. **Backend test database setup:** test setup now uses a temporary file-backed SQLite database and the complete backend suite passes in the current run.

### Open blockers

1. **Real pipeline completion is unverified:** the current run reached `roadmap` but did not reach a terminal state during the observation window.
2. **ARQ duplicate-lock messages:** the worker repeatedly logs `job ... already running elsewhere` while the active long-running job is executing. This needs production-style worker/job-lock investigation and timeout/recovery validation.
3. **Ollama throughput:** the local `gemma2:2b` model is too slow for a complete 14-stage smoke test within a short test window. Request timeouts and user-visible long-running state should be validated.
4. **External dependencies:** PostgreSQL, Whisper, search credentials, Puter authorization, and Docker were unavailable or untested.
5. **Frontend lint warnings:** no errors remain, but 80 warnings include unused imports/variables and React hook dependency warnings that should be cleaned before release.

## Performance profile added after testing

The local Ollama pipeline now uses a performance-oriented profile: 2,048-token context, 2,048-token output cap, temperature `0.2`, a 10-minute model keep-alive, and one attempt per stage. This intentionally reduces reasoning depth and retry time while preserving one-by-one stage execution and schema validation. A warm `gemma2:2b` request measured approximately 0.38 seconds after an initial model load.

## Data and test isolation

The smoke tests created local `qa-...@example.com` accounts and test projects in `backend/dev_fallback.db`. These are development-only records and should be removed or the fallback database reset before sharing the environment.

## Readiness assessment

The platform is suitable for continued local development and targeted UI/API testing. It should **not** be marked production-ready until a real pipeline run reaches `workflow:completed` with a persisted blueprint, the ARQ lock behavior is resolved or proven safe, browser-based meeting flows are exercised, and the production dependency matrix is validated with PostgreSQL, a transcription service, configured search credentials, and a containerized deployment.
