"""Live smoke test against the running adb-api server (real adb binary).

Hits GET /health and POST /adb/exec {"command": "devices"} and prints the
structured JSON responses. Requires the server to be already listening on
the given host/port (started via ``main.py --no-gui --port 8001``).
"""

import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8001"


def _request(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def main():
    print("== GET /health ==")
    status, body = _request("GET", "/health")
    print("HTTP", status)
    print(json.dumps(body, ensure_ascii=False, indent=2))
    assert status == 200, "health should be 200"
    assert body.get("success") is True
    assert "adb_available" in body["data"]

    print("\n== POST /adb/exec {\"command\": \"devices\"} ==")
    status, body = _request("POST", "/adb/exec", {"command": "devices"})
    print("HTTP", status)
    print(json.dumps(body, ensure_ascii=False, indent=2))
    assert status == 200, "exec should be 200"
    assert body.get("success") is True

    print("\nLIVE SMOKE TEST OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
