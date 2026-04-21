import fakeredis
import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def fake_redis(monkeypatch):
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(main, "r", fake)
    yield fake
    fake.flushall()


@pytest.fixture
def client(fake_redis):
    return TestClient(main.app)


def test_health_ok_when_redis_reachable(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_create_job_enqueues_and_sets_status(client, fake_redis):
    res = client.post("/jobs")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "queued"
    job_id = body["job_id"]

    # job id was pushed onto the queue
    assert fake_redis.llen(main.QUEUE_KEY) == 1
    assert fake_redis.lrange(main.QUEUE_KEY, 0, -1) == [job_id]
    # status hash was written
    assert fake_redis.hget(f"job:{job_id}", "status") == "queued"


def test_get_job_returns_404_for_unknown_id(client):
    res = client.get("/jobs/does-not-exist")
    assert res.status_code == 404


def test_get_job_returns_current_status(client, fake_redis):
    fake_redis.hset("job:abc-123", "status", "processing")
    res = client.get("/jobs/abc-123")
    assert res.status_code == 200
    assert res.json() == {"job_id": "abc-123", "status": "processing"}
