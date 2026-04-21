import sys
import urllib.request

URL = "http://127.0.0.1:8000/health"

try:
    with urllib.request.urlopen(URL, timeout=2) as resp:
        sys.exit(0 if resp.status == 200 else 1)
except Exception:
    sys.exit(1)
