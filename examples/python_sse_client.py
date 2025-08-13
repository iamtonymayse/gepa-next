import os
from sseclient import SSEClient

BASE = os.getenv("BASE_URL", "http://localhost:8000")
TOKEN = os.getenv("API_BEARER_TOKEN", "change-me")


def stream(job_id: str, last_id: int | None = None):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    url = f"{BASE}/v1/optimize/{job_id}/events"
    if last_id is not None:
        headers["Last-Event-ID"] = str(last_id)
    messages = SSEClient(url, headers=headers)
    for msg in messages:
        if msg.event is None and msg.data == "":
            continue  # ping
        print(f"{msg.event or 'message'}: {msg.data}")


if __name__ == "__main__":
    import sys

    stream(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else None)
