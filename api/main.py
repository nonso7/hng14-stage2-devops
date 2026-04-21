import logging
import os
import uuid

import redis
from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
QUEUE_KEY = os.environ.get("QUEUE_KEY", "job_queue")

app = FastAPI(title="job-api")
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


@app.get("/health")
def health():
    try:
        r.ping()
    except redis.RedisError as exc:
        log.warning("redis ping failed: %s", exc)
        raise HTTPException(status_code=503, detail="redis unavailable")
    return {"status": "ok"}


@app.post("/jobs")
def create_job():
    job_id = str(uuid.uuid4())
    r.hset(f"job:{job_id}", "status", "queued")
    r.lpush(QUEUE_KEY, job_id)
    return {"job_id": job_id, "status": "queued"}


@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    status = r.hget(f"job:{job_id}", "status")
    if status is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {"job_id": job_id, "status": status}
