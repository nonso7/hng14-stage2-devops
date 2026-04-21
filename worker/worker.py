import logging
import os
import signal
import sys
import time

import redis

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("worker")

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
QUEUE_KEY = os.environ.get("QUEUE_KEY", "job_queue")
HEARTBEAT_KEY = os.environ.get("HEARTBEAT_KEY", "worker:heartbeat")
HEARTBEAT_TTL = int(os.environ.get("HEARTBEAT_TTL", "15"))
JOB_DURATION = int(os.environ.get("JOB_DURATION", "2"))
POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "5"))

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

_running = True


def _stop(signum, _frame):
    global _running
    log.info("received signal %s, shutting down", signum)
    _running = False


signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)


def heartbeat() -> None:
    try:
        r.set(HEARTBEAT_KEY, "ok", ex=HEARTBEAT_TTL)
    except redis.RedisError as exc:
        log.warning("heartbeat write failed: %s", exc)


def process_job(job_id: str) -> None:
    log.info("processing job %s", job_id)
    r.hset(f"job:{job_id}", "status", "processing")
    time.sleep(JOB_DURATION)
    r.hset(f"job:{job_id}", "status", "completed")
    log.info("completed job %s", job_id)


def main() -> int:
    log.info(
        "worker starting; queue=%s redis=%s:%s", QUEUE_KEY, REDIS_HOST, REDIS_PORT
    )
    while _running:
        heartbeat()
        try:
            job = r.brpop(QUEUE_KEY, timeout=POLL_TIMEOUT)
        except redis.RedisError as exc:
            log.error("redis error polling queue: %s", exc)
            time.sleep(1)
            continue
        if not job:
            continue
        _, job_id = job
        try:
            process_job(job_id)
        except redis.RedisError as exc:
            log.error("error processing %s: %s", job_id, exc)
    log.info("worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
