# FIXES

Each entry lists the file, the original line, the problem, and the change applied.
Line numbers refer to the **original** starter code.

---

## api/main.py

### 1. Hardcoded Redis host and port — L8
**Was:** `r = redis.Redis(host="localhost", port=6379)`
**Problem:** `localhost` inside the API container resolves to the container itself, not Redis. Breaks as soon as the app runs in Docker/Compose.
**Fix:** Read `REDIS_HOST` and `REDIS_PORT` from the environment with sane defaults (`redis`, `6379`). Also set `decode_responses=True` so callers receive `str`, not `bytes`.

### 2. Missing `/health` endpoint
**Problem:** The task requires every service to have a working `HEALTHCHECK`, and Compose must start services only after dependencies are *healthy*. FastAPI had no health route.
**Fix:** Added `GET /health` that pings Redis and returns `200 {"status":"ok"}` on success, `503` otherwise.

### 3. Unused import — L4
**Was:** `import os` (never used).
**Problem:** Dead import; lint failure under `flake8`.
**Fix:** `os` is now actually used for env lookups, so the import is valid.

### 4. Non-atomic enqueue — L13–14
**Was:**
```python
r.lpush("job", job_id)
r.hset(f"job:{job_id}", "status", "queued")
```
**Problem:** Worker can `BRPOP` the id before the status hash exists, causing a race where a status lookup briefly returns 404 for a valid job.
**Fix:** Write the status hash **first**, then push to the queue.

### 5. Wrong status code for missing job — L21
**Was:** `return {"error": "not found"}` with implicit HTTP 200.
**Problem:** Callers can't distinguish "job missing" from a real response. The frontend keeps polling forever.
**Fix:** `raise HTTPException(status_code=404, detail="job not found")`.

### 6. Queue key too similar to hash prefix — L13
**Was:** queue list was `"job"`; per-job hash was `"job:<id>"`.
**Problem:** Legal in Redis (different key types) but confusing to read.
**Fix:** Queue list renamed to `"job_queue"` (via `QUEUE_KEY` env var). Worker updated to match.

---

## worker/worker.py

### 7. Hardcoded Redis host — L6
**Was:** `r = redis.Redis(host="localhost", port=6379)`
**Problem:** Same issue as the API — won't reach Redis across Compose services.
**Fix:** Env-driven `REDIS_HOST` / `REDIS_PORT`, `decode_responses=True`.

### 8. `signal` imported but never wired up — L4, L14
**Was:** `import signal` at the top, but the `while True:` loop never installs a handler.
**Problem:** `docker stop` sends SIGTERM, which the process ignores. Docker waits the stop grace period (10s default) and then SIGKILLs it mid-job.
**Fix:** Registered SIGTERM and SIGINT handlers that flip a `_running` flag; the main loop exits cleanly and logs shutdown.

### 9. Unused `os` import — L3
**Was:** `import os` (never used).
**Fix:** Now used for `os.environ.get(...)`.

### 10. No liveness signal for HEALTHCHECK
**Problem:** The worker is a background loop with no HTTP surface. A Dockerfile `HEALTHCHECK` needs something to check.
**Fix:** Each loop iteration writes `worker:heartbeat` to Redis with a TTL (`HEARTBEAT_TTL`, default 15s). The Dockerfile's HEALTHCHECK runs a small script that asserts the key is present.

### 11. No error handling around Redis — L15, L11
**Problem:** A transient `ConnectionError` crashes the worker; Compose restarts it but in-flight work is lost silently.
**Fix:** Wrapped the `BRPOP` poll and `process_job` in `try/except redis.RedisError`; errors are logged and the loop continues after a short back-off.

### 12. `print` instead of logging — L9, L12
**Problem:** No timestamps, no levels, no way to filter noise in aggregated logs.
**Fix:** Switched to the stdlib `logging` module with a standard format.

### 13. No "processing" status written — L10–11
**Was:** Status jumped straight from `queued` → `completed`.
**Problem:** Frontend can't tell whether a job is still in the queue or actively running.
**Fix:** Write `status=processing` before the sleep, `status=completed` after.

---

## frontend/app.js

### 14. Hardcoded API URL — L6
**Was:** `const API_URL = "http://localhost:8000";`
**Problem:** Inside a container, `localhost` is the frontend container itself. Submits and status lookups fail.
**Fix:** `const API_URL = process.env.API_URL || 'http://api:8000';` — Compose-service default, env-overridable.

### 15. Hardcoded port — L29
**Was:** `app.listen(3000, ...)`.
**Fix:** `const PORT = parseInt(process.env.PORT || '3000', 10);` — env-overridable.

### 16. Missing `/health` endpoint
**Problem:** Dockerfile HEALTHCHECK needs a route.
**Fix:** Added `GET /health` that pings the upstream API's `/health` and returns 200 only if the API is reachable.

### 17. 404 masked as 500 — L25
**Was:** any axios error returned `500 {"error": "something went wrong"}`.
**Problem:** A legitimate "job not found" (404) is indistinguishable from "API is down" (502). Also breaks the frontend polling loop.
**Fix:** Forward 404 as 404, surface other upstream failures as 502.

---

## frontend/views/index.html

### 18. Polling loops forever on non-"completed" statuses — L35
**Was:** `if (data.status !== 'completed') { setTimeout(...) }`
**Problem:** On `failed`, or when `data.status` is `undefined` (e.g. 404 payload), the UI polls forever every 2s.
**Fix:** Stop polling when status is `completed`, `failed`, or missing.

---

## Dependency hygiene

### 19. Unpinned Python deps — api/requirements.txt, worker/requirements.txt
**Was:** bare `fastapi`, `uvicorn`, `redis` with no versions.
**Problem:** Image rebuilds are non-reproducible; a future breaking release silently breaks production.
**Fix:** Pinned to known-good versions. `uvicorn` upgraded to `uvicorn[standard]` so it ships the performant defaults (`uvloop`, `httptools`).

### 20. Missing Node engines field — frontend/package.json
**Problem:** Nothing declares the supported Node version; CI and Docker could diverge silently.
**Fix:** Added `"engines": { "node": ">=20" }`.

---

## Repository hygiene

### 21. `.env` committed in the starter — api/.env
**Was:** The starter's first commit (`a98a2d1`) included `api/.env` containing:
```
REDIS_PASSWORD=supersecretpassword123
APP_ENV=production
```
**Problem:** The task explicitly forbids `.env` from appearing in the repo or git history. Neither variable is referenced anywhere in the application code — they are dead/leftover values from the starter.
**Fix:** Deleted the file from the working tree; `.gitignore` excludes `.env` at any path; the file must also be purged from git history via `git filter-branch` before pushing (see README / runbook).
