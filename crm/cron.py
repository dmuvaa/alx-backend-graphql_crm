# crm/cron.py
from datetime import datetime
import json
import os

# Optional GraphQL health ping
try:
    import requests
except Exception:
    requests = None

LOG_FILE = "/tmp/crm_heartbeat_log.txt"
GRAPHQL_URL = os.getenv("GRAPHQL_URL", "http://localhost:8000/graphql")

def log_crm_heartbeat():
    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    msg = f"{ts} CRM is alive"

    # Optional GraphQL hello check (best-effort; never block logging)
    gql_status = ""
    if requests is not None:
        try:
            payload = {"query": "{ hello }"}
            r = requests.post(GRAPHQL_URL, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=5)
            if r.ok:
                data = r.json().get("data", {})
                if data.get("hello") == "Hello, GraphQL!":
                    gql_status = " | GraphQL: OK"
                else:
                    gql_status = " | GraphQL: Unexpected response"
            else:
                gql_status = f" | GraphQL: HTTP {r.status_code}"
        except Exception as e:
            gql_status = f" | GraphQL: ERR {e.__class__.__name__}"

    # Append log line
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + gql_status + "\n")
