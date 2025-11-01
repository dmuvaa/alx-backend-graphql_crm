# crm/schema.py
import graphene
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from graphene_django import DjangoObjectType

from .models import Customer, Product, Order


# ----------------------------
# GraphQL Object Types
# ----------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# ----------------------------
# Inputs (field names match Checkpoint)
# ----------------------------
class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)  # exposed as Float, stored as Decimal
    stock = graphene.Int(required=False, default_value=0)


class CreateOrderInput(graphene.InputObjectType):
    # IMPORTANT: use GraphQL camelCase names to match your Checkpoint mutations
    customer_id = graphene.ID(required=True, name="customerId")
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True, name="productIds")
    order_date = graphene.DateTime(required=False, name="orderDate")


# ----------------------------
# Mutations
# ----------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input: CreateCustomerInput):
        # Uniqueness (friendly error)
        if Customer.objects.filter(email__iexact=input.email).exists():
            return CreateCustomer(customer=None, message="Failed", errors=["Email already exists"])

        try:
            cust = Customer(name=input.name, email=input.email, phone=(input.phone or None))
            cust.full_clean()  # runs model validators (email/phone)
            cust.save()
            return CreateCustomer(customer=cust, message="Customer created", errors=[])
        except ValidationError as e:
            human = [f"{fld}: {msg}" for fld, msgs in e.message_dict.items() for msg in msgs]
            return CreateCustomer(customer=None, message="Failed", errors=human)
        except IntegrityError:
            return CreateCustomer(customer=None, message="Failed", errors=["Email already exists"])


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CreateCustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input):
        created = []
        errs = []

        # Partial success: isolate each insert in its own atomic block
        for idx, row in enumerate(input):
            try:
                if Customer.objects.filter(email__iexact=row.email).exists():
                    errs.append(f"[{idx}] Email already exists: {row.email}")
                    continue

                cust = Customer(name=row.name, email=row.email, phone=(row.phone or None))
                cust.full_clean()
                with transaction.atomic():
                    cust.save()
                created.append(cust)
            except ValidationError as e:
                for fld, msgs in e.message_dict.items():
                    for msg in msgs:
                        errs.append(f"[{idx}] {fld}: {msg}")
            except IntegrityError:
                errs.append(f"[{idx}] Email already exists: {row.email}")

        return BulkCreateCustomers(customers=created, errors=errs)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = CreateProductInput(required=True)

    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input: CreateProductInput):
        problems = []

        # Validate numerics
        try:
            price = Decimal(str(input.price))
            if price <= 0:
                problems.append("price must be > 0")
        except Exception:
            problems.append("price must be a valid number")

        stock = input.stock if input.stock is not None else 0
        if stock < 0:
            problems.append("stock must be >= 0")

        if problems:
            return CreateProduct(product=None, errors=problems)

        try:
            p = Product(name=input.name, price=price, stock=stock)
            p.full_clean()
            p.save()
            return CreateProduct(product=p, errors=[])
        except ValidationError as e:
            human = [f"{fld}: {msg}" for fld, msgs in e.message_dict.items() for msg in msgs]
            return CreateProduct(product=None, errors=human)


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = CreateOrderInput(required=True)

    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input: CreateOrderInput):
        # Validate customer
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            return CreateOrder(order=None, errors=[f"Invalid customer ID: {input.customer_id}"])

        # Validate products
        if not input.product_ids:
            return CreateOrder(order=None, errors=["At least one product must be selected"])

        products = list(Product.objects.filter(pk__in=input.product_ids))
        missing = set(map(str, input.product_ids)) - set(map(lambda p: str(p.pk), products))
        if missing:
            return CreateOrder(order=None, errors=[f"Invalid product ID(s): {', '.join(sorted(missing))}"])

        # Create atomically; compute total using Decimal for accuracy
        with transaction.atomic():
            odt = input.order_date or timezone.now()
            order = Order.objects.create(customer=customer, order_date=odt, total_amount=Decimal("0.00"))
            order.products.set(products)
            total = sum((p.price for p in products), Decimal("0.00"))
            order.total_amount = total
            order.save()

        return CreateOrder(order=order, errors=[])


# ----------------------------
# Root Query & Mutation for this app
# ----------------------------
class Query(graphene.ObjectType):
    # Keep your hello for quick checks
    hello = graphene.String(default_value="Hello, GraphQL!")

    # Simple lists for visibility/testing
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    def resolve_customers(root, info):
        return Customer.objects.all()

    def resolve_products(root, info):
        return Product.objects.all()

    def resolve_orders(root, info):
        return Order.objects.select_related("customer").prefetch_related("products").all()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
