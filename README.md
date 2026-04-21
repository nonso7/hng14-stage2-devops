# hng14-stage2-devops — Job Processing System

Three-service job processor packaged as a Compose stack with a GitHub Actions
CI/CD pipeline.

- **api** (Python / FastAPI) — creates jobs, reports status
- **worker** (Python) — pulls jobs off a Redis queue and processes them
- **frontend** (Node.js / Express) — submits jobs and renders status
- **redis** — shared queue + state store (not exposed to the host)

Every container runs as a non-root user, has a working `HEALTHCHECK`, and
is built from a multi-stage image that contains no build tools in the
runtime layer. All configuration is driven by environment variables — no
secrets or `.env` files ever enter an image.

---

## Prerequisites

- Docker Engine **24+**
- Docker Compose **v2** (shipped with modern Docker Desktop / `docker-compose-plugin`)
- `bash`, `curl`, and `python3` on the host (for scripts)
- Python **3.12** and Node **20** (only needed if you want to run tests or lint locally — not needed to bring the stack up)

Verify:
```bash
docker --version
docker compose version
```

---

## 1. Bring the stack up on a clean machine

```bash
git clone https://github.com/<your-user>/hng14-stage2-devops.git
cd hng14-stage2-devops

# Copy env template — never edit .env.example for real values
cp .env.example .env

# Build all images and wait for every service to pass its healthcheck
docker compose up -d --build --wait --wait-timeout 120
```

### What a successful startup looks like

```bash
$ docker compose ps
NAME              IMAGE                 STATUS                  PORTS
jobapp-api-1      job-api:latest        Up (healthy)            0.0.0.0:8000->8000/tcp
jobapp-frontend-1 job-frontend:latest   Up (healthy)            0.0.0.0:3000->3000/tcp
jobapp-redis-1    redis:7-alpine        Up (healthy)
jobapp-worker-1   job-worker:latest     Up (healthy)
```

All four services must read `Up (healthy)`. Redis has **no** host port
mapping — that's by design.

Open the dashboard at **http://localhost:3000** and click *Submit New Job*.
The UI will poll until the status reaches `completed`.

### Smoke test from the CLI

```bash
# Submit a job through the frontend
curl -X POST http://localhost:3000/submit
# -> {"job_id":"<uuid>","status":"queued"}

# Poll status
curl http://localhost:3000/status/<uuid>
# -> {"job_id":"<uuid>","status":"completed"}
```

Or run the full scripted flow:
```bash
bash scripts/integration-test.sh
```

### Tear down

```bash
docker compose down -v
```

---

## 2. Configuration

All settings live in `.env`. The committed `.env.example` lists every
required variable with placeholder values.

| Variable | Purpose |
|---|---|
| `COMPOSE_PROJECT_NAME` | Prefix for container names |
| `API_IMAGE`, `WORKER_IMAGE`, `FRONTEND_IMAGE`, `IMAGE_TAG` | Image name/tag used by Compose |
| `REDIS_HOST`, `REDIS_PORT` | Redis address on the internal network |
| `QUEUE_KEY` | Redis list used as the job queue |
| `HEARTBEAT_KEY`, `HEARTBEAT_TTL` | Worker liveness key (for HEALTHCHECK) |
| `JOB_DURATION` | Simulated work time in the worker |
| `API_URL` | How the frontend reaches the API over the internal network |
| `API_PORT`, `FRONTEND_PORT` | Host-facing port mappings |

`.env` is git-ignored and is never copied into any image.

---

## 3. Running the pipeline stages locally

### Lint
```bash
pip install flake8
flake8 api worker

cd frontend && npm install --no-save eslint@^9 && npx eslint app.js healthcheck.js

# Dockerfiles
docker run --rm -i hadolint/hadolint < api/Dockerfile
docker run --rm -i hadolint/hadolint < worker/Dockerfile
docker run --rm -i hadolint/hadolint < frontend/Dockerfile
```

### Unit tests (Redis is mocked with `fakeredis`)
```bash
cd api
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term
```

### Security scan
```bash
docker compose build
trivy image --severity CRITICAL --exit-code 1 job-api:latest
trivy image --severity CRITICAL --exit-code 1 job-worker:latest
trivy image --severity CRITICAL --exit-code 1 job-frontend:latest
```

### Rolling deploy simulation
```bash
# Start the stack, then roll the worker (or the api):
docker compose up -d --wait
bash scripts/rolling-deploy.sh worker
```
The script brings up a replacement container, waits up to 60 s for its
HEALTHCHECK to pass, then stops the old one. If the timeout expires, the
replacement is removed and the old container is left running.

---

## 4. CI/CD pipeline

GitHub Actions workflow: [.github/workflows/ci.yml](.github/workflows/ci.yml)

Stages run strictly in order; a failure in any stage prevents every stage
that follows:

```
lint → test → build → security-scan → integration-test → deploy
```

- **lint** — flake8, eslint, hadolint
- **test** — pytest with coverage; coverage XML uploaded as an artifact
- **build** — builds all three images, tags each with the short git SHA and
  `latest`, pushes to a local `registry:2` running as a **job service
  container**, then saves tarballs for downstream jobs
- **security-scan** — Trivy against each image; any `CRITICAL` finding
  fails the job. SARIF reports uploaded as an artifact
- **integration-test** — brings the full Compose stack up inside the
  runner, submits a job, polls until the final status is `completed`, tears
  the stack down cleanly regardless of outcome
- **deploy** — only runs on pushes to `main`. Invokes the rolling-deploy
  script, which aborts and leaves the old container running if the new
  container's HEALTHCHECK does not pass within 60 seconds

---

## 5. Layout

```
.
├── api/                     FastAPI service
│   ├── Dockerfile
│   ├── main.py
│   ├── healthcheck.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── tests/test_api.py
├── worker/                  Queue consumer
│   ├── Dockerfile
│   ├── worker.py
│   └── healthcheck.py
├── frontend/                Express UI
│   ├── Dockerfile
│   ├── app.js
│   ├── healthcheck.js
│   └── views/index.html
├── scripts/
│   ├── integration-test.sh
│   └── rolling-deploy.sh
├── .github/workflows/ci.yml
├── docker-compose.yml
├── .env.example
├── FIXES.md                 Every bug found in the starter code
└── README.md
```

---

## 6. Bug fixes in the starter

Every bug fixed in the starter is documented in [FIXES.md](FIXES.md) —
file, original line number, the problem, and the change applied.
