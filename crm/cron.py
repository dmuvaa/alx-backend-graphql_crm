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

LOW_STOCK_LOG = "/tmp/low_stock_updates_log.txt"
GRAPHQL_URL = os.getenv("GRAPHQL_URL", "http://localhost:8000/graphql")

def update_low_stock():
    """
    Runs the UpdateLowStockProducts GraphQL mutation and logs updated products.
    Appends lines like:
    [YYYY-MM-DD HH:MM:SS] Restocked: Laptop -> stock=18
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    transport = RequestsHTTPTransport(
        url=GRAPHQL_URL,
        headers={"Content-Type": "application/json"},
        verify=True,
        retries=2,
        timeout=10,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    mutation = gql("""
      mutation {
        updateLowStockProducts {
          message
          products { id name stock }
        }
      }
    """)

    try:
        res = client.execute(mutation)
        payload = (res or {}).get("updateLowStockProducts") or {}
        products = payload.get("products") or []
        message = payload.get("message") or "Done."
    except Exception as e:
        # Log the error line and exit
        with open(LOW_STOCK_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] ERROR: {e.__class__.__name__}: {e}\n")
        return

    # Log each updated product
    with open(LOW_STOCK_LOG, "a", encoding="utf-8") as f:
        if not products:
            f.write(f"[{ts}] No low-stock products to restock. ({message})\n")
        else:
            for p in products:
                f.write(f"[{ts}] Restocked: {p.get('name')} -> stock={p.get('stock')}\n")
