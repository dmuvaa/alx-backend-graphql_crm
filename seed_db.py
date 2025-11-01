# seed_db.py
import os
import django
from decimal import Decimal
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product, Order  # noqa

def run():
    # Customers
    c1, _ = Customer.objects.get_or_create(name="Alice", email="alice@example.com", phone="+1234567890")
    c2, _ = Customer.objects.get_or_create(name="Bob", email="bob@example.com")
    c3, _ = Customer.objects.get_or_create(name="Carol", email="carol@example.com", phone="123-456-7890")

    # Products
    p1, _ = Product.objects.get_or_create(name="Laptop", price=Decimal("999.99"), stock=10)
    p2, _ = Product.objects.get_or_create(name="Mouse", price=Decimal("25.50"), stock=100)
    p3, _ = Product.objects.get_or_create(name="Keyboard", price=Decimal("45.00"), stock=50)

    # One example order
    order = Order.objects.create(customer=c1, order_date=timezone.now(), total_amount=Decimal("0.00"))
    order.products.set([p1, p2])
    order.total_amount = p1.price + p2.price
    order.save()

    print("Seed complete.")
    print(f"Customers: {Customer.objects.count()}, Products: {Product.objects.count()}, Orders: {Order.objects.count()}")

if __name__ == "__main__":
    run()
