import os
import sys

try:
    import redis
except ImportError:
    sys.exit(2)

HOST = os.environ.get("REDIS_HOST", "redis")
PORT = int(os.environ.get("REDIS_PORT", "6379"))
KEY = os.environ.get("HEARTBEAT_KEY", "worker:heartbeat")

try:
    client = redis.Redis(
        host=HOST, port=PORT, socket_timeout=2, socket_connect_timeout=2
    )
    sys.exit(0 if client.exists(KEY) else 1)
except Exception:
    sys.exit(1)
