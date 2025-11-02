# crm/cron.py
from datetime import datetime
import os
from gql.transport.requests import RequestsHTTPTransport
from gql import gql, Client

LOG_FILE = "/tmp/crm_heartbeat_log.txt"
GRAPHQL_URL = os.getenv("GRAPHQL_URL", "http://localhost:8000/graphql")

def log_crm_heartbeat():
    """
    Append a heartbeat line to /tmp/crm_heartbeat_log.txt in the format:
    DD/MM/YYYY-HH:MM:SS CRM is alive [ | GraphQL: OK/… ]
    """
    ts = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    gql_status = ""

    try:
        transport = RequestsHTTPTransport(
            url=GRAPHQL_URL,
            headers={"Content-Type": "application/json"},
            verify=True,
            retries=2,
            timeout=5,
        )
        client = Client(transport=transport, fetch_schema_from_transport=False)
        result = client.execute(gql("{ hello }"))
        if result and result.get("hello") == "Hello, GraphQL!":
            gql_status = " | GraphQL: OK"
        else:
            gql_status = " | GraphQL: Unexpected response"
    except Exception as e:
        gql_status = f" | GraphQL: ERR {e.__class__.__name__}"

    line = f"{ts} CRM is alive{gql_status}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
