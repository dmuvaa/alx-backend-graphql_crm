mkdir -p crm/cron_jobs
cat > crm/cron_jobs/send_order_reminders.py <<'PY'
#!/usr/bin/env python3
import sys
from datetime import datetime, timedelta, timezone

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

ENDPOINT = "http://localhost:8000/graphql"
LOG_FILE = "/tmp/order_reminders_log.txt"

def iso(dt: datetime) -> str:
    # Ensure ISO-8601 with timezone (UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()

def main():
    now = datetime.now(timezone.utc)
    gte = now - timedelta(days=7)
    lte = now

    transport = RequestsHTTPTransport(
        url=ENDPOINT,
        verify=True,
        retries=3,
        headers={"Content-Type": "application/json"},
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    query = gql("""
      query ($gte: DateTime!, $lte: DateTime!) {
        allOrders(filter: { orderDateGte: $gte, orderDateLte: $lte }) {
          edges {
            node {
              id
              orderDate
              customer { email }
            }
          }
        }
      }
    """)

    result = client.execute(query, variable_values={"gte": iso(gte), "lte": iso(lte)})

    edges = (result or {}).get("allOrders", {}).get("edges", [])
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Append logs
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        for edge in edges:
            node = edge.get("node", {})
            order_id = node.get("id")
            email = (node.get("customer") or {}).get("email")
            f.write(f"[{ts}] OrderID={order_id} -> {email}\n")

    print("Order reminders processed!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Fail loudly for cron diagnostics, but don’t swallow the exception.
        print(f"ERROR: {e}", file=sys.stderr)
        raise
PY

chmod +x crm/cron_jobs/send_order_reminders.py
