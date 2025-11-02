# crm/tasks.py
from datetime import datetime
import os

from celery import shared_task
from gql.transport.requests import RequestsHTTPTransport
from gql import gql, Client

GRAPHQL_URL = os.getenv("GRAPHQL_URL", "http://localhost:8000/graphql")
LOG_FILE = "/tmp/crm_report_log.txt"

@shared_task
def generate_crm_report():
    """
    Generates a weekly CRM report:
      - total customers
      - total orders
      - total revenue (sum of order.totalAmount)
    Logs to /tmp/crm_report_log.txt:
      YYYY-MM-DD HH:MM:SS - Report: X customers, Y orders, Z revenue
    """
    transport = RequestsHTTPTransport(
        url=GRAPHQL_URL,
        headers={"Content-Type": "application/json"},
        verify=True,
        retries=3,
        timeout=15,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    # Use simple list fields defined in your schema (customers, orders)
    query = gql("""
      query {
        customers { id }
        orders { id totalAmount }
      }
    """)

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = client.execute(query)
        customers = result.get("customers", []) or []
        orders = result.get("orders", []) or []
        total_customers = len(customers)
        total_orders = len(orders)
        total_revenue = 0.0
        for o in orders:
            # Graphene may serialize Decimal as string; coerce to float safely
            val = o.get("totalAmount")
            try:
                total_revenue += float(val)
            except Exception:
                pass

        line = f"{ts} - Report: {total_customers} customers, {total_orders} orders, {total_revenue:.2f} revenue\n"
    except Exception as e:
        line = f"{ts} - Report ERROR: {e.__class__.__name__}: {e}\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
