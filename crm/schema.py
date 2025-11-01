# crm/schema.py
import graphene
from decimal import Decimal
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField

from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter

# ----------------------------------------------------
# Types used by mutations (keep as-is)
# ----------------------------------------------------
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone", "created_at")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock", "created_at")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date", "created_at")

# ----------------------------------------------------
# Relay Node types for filtered connections
# ----------------------------------------------------
class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (graphene.relay.Node,)
        fields = ("id", "name", "email", "phone", "created_at")

class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (graphene.relay.Node,)
        fields = ("id", "name", "price", "stock", "created_at")

class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (graphene.relay.Node,)
        fields = ("id", "customer", "products", "total_amount", "order_date", "created_at")

# ----------------------------------------------------
# Inputs (field names match your checkpoint)
# ----------------------------------------------------
class CreateCustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class CreateProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Float(required=True)  # exposed as Float, stored as Decimal
    stock = graphene.Int(required=False, default_value=0)

class CreateOrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True, name="customerId")
    product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True, name="productIds")
    order_date = graphene.DateTime(required=False, name="orderDate")

# ----------------------------------------------------
# Filter input helpers (camelCase keys for your checkpoints)
# ----------------------------------------------------
class CustomerFilterInput(graphene.InputObjectType):
    name_icontains = graphene.String(name="nameIcontains")
    email_icontains = graphene.String(name="emailIcontains")
    created_at_gte = graphene.Date(name="createdAtGte")
    created_at_lte = graphene.Date(name="createdAtLte")
    phone_pattern = graphene.String(name="phonePattern")

class ProductFilterInput(graphene.InputObjectType):
    name_icontains = graphene.String(name="nameIcontains")
    price_gte = graphene.Float(name="priceGte")
    price_lte = graphene.Float(name="priceLte")
    stock_gte = graphene.Int(name="stockGte")
    stock_lte = graphene.Int(name="stockLte")

class OrderFilterInput(graphene.InputObjectType):
    total_amount_gte = graphene.Float(name="totalAmountGte")
    total_amount_lte = graphene.Float(name="totalAmountLte")
    order_date_gte = graphene.DateTime(name="orderDateGte")
    order_date_lte = graphene.DateTime(name="orderDateLte")
    customer_name = graphene.String(name="customerName")
    product_name = graphene.String(name="productName")
    product_id = graphene.ID(name="productId")

# Safelists for orderBy
CUSTOMER_ORDERABLE = {"name", "-name", "email", "-email", "created_at", "-created_at"}
PRODUCT_ORDERABLE = {"name", "-name", "price", "-price", "stock", "-stock", "created_at", "-created_at"}
ORDER_ORDERABLE = {"order_date", "-order_date", "total_amount", "-total_amount", "created_at", "-created_at"}

# ----------------------------------------------------
# Mutations (unchanged from your current file)
# ----------------------------------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CreateCustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, input: CreateCustomerInput):
        if Customer.objects.filter(email__iexact=input.email).exists():
            return CreateCustomer(customer=None, message="Failed", errors=["Email already exists"])
        try:
            cust = Customer(name=input.name, email=input.email, phone=(input.phone or None))
            cust.full_clean()
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
        created, errs = [], []
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
        try:
            customer = Customer.objects.get(pk=input.customer_id)
        except Customer.DoesNotExist:
            return CreateOrder(order=None, errors=[f"Invalid customer ID: {input.customer_id}"])

        if not input.product_ids:
            return CreateOrder(order=None, errors=["At least one product must be selected"])

        products = list(Product.objects.filter(pk__in=input.product_ids))
        missing = set(map(str, input.product_ids)) - set(map(lambda p: str(p.pk), products))
        if missing:
            return CreateOrder(order=None, errors=[f"Invalid product ID(s): {', '.join(sorted(missing))}"])

        with transaction.atomic():
            odt = input.order_date or timezone.now()
            order = Order.objects.create(customer=customer, order_date=odt, total_amount=Decimal("0.00"))
            order.products.set(products)
            total = sum((p.price for p in products), Decimal("0.00"))
            order.total_amount = total
            order.save()

        return CreateOrder(order=order, errors=[])

# ----------------------------------------------------
# Query: add filtered connections + orderBy
# ----------------------------------------------------
class Query(graphene.ObjectType):
    # simple ping
    hello = graphene.String(default_value="Hello, GraphQL!")

    # Relay-style, filterable, sortable
    all_customers = DjangoFilterConnectionField(
        CustomerNode,
        filterset_class=CustomerFilter,
        filter=CustomerFilterInput(),
        order_by=graphene.String(name="orderBy"),
    )
    all_products = DjangoFilterConnectionField(
        ProductNode,
        filterset_class=ProductFilter,
        filter=ProductFilterInput(),
        order_by=graphene.String(name="orderBy"),
    )
    all_orders = DjangoFilterConnectionField(
        OrderNode,
        filterset_class=OrderFilter,
        filter=OrderFilterInput(),
        order_by=graphene.String(name="orderBy"),
    )

    # Keep the simple list fields (optional, handy for debug)
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    # Apply friendly filter + orderBy manually on top of django-filter
    def resolve_all_customers(self, info, filter=None, order_by=None, **kwargs):
        qs = Customer.objects.all()
        if filter:
            if filter.get("name_icontains"):
                qs = qs.filter(name__icontains=filter["name_icontains"])
            if filter.get("email_icontains"):
                qs = qs.filter(email__icontains=filter["email_icontains"])
            if filter.get("created_at_gte"):
                qs = qs.filter(created_at__gte=filter["created_at_gte"])
            if filter.get("created_at_lte"):
                qs = qs.filter(created_at__lte=filter["created_at_lte"])
            if filter.get("phone_pattern"):
                qs = qs.filter(phone__startswith=filter["phone_pattern"])
        if order_by and order_by in {"name", "-name", "email", "-email", "created_at", "-created_at"}:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_products(self, info, filter=None, order_by=None, **kwargs):
        qs = Product.objects.all()
        if filter:
            if filter.get("name_icontains"):
                qs = qs.filter(name__icontains=filter["name_icontains"])
            if filter.get("price_gte") is not None:
                qs = qs.filter(price__gte=filter["price_gte"])
            if filter.get("price_lte") is not None:
                qs = qs.filter(price__lte=filter["price_lte"])
            if filter.get("stock_gte") is not None:
                qs = qs.filter(stock__gte=filter["stock_gte"])
            if filter.get("stock_lte") is not None:
                qs = qs.filter(stock__lte=filter["stock_lte"])
        if order_by and order_by in {"name", "-name", "price", "-price", "stock", "-stock", "created_at", "-created_at"}:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_orders(self, info, filter=None, order_by=None, **kwargs):
        qs = Order.objects.select_related("customer").prefetch_related("products").all()
        if filter:
            if filter.get("total_amount_gte") is not None:
                qs = qs.filter(total_amount__gte=filter["total_amount_gte"])
            if filter.get("total_amount_lte") is not None:
                qs = qs.filter(total_amount__lte=filter["total_amount_lte"])
            if filter.get("order_date_gte"):
                qs = qs.filter(order_date__gte=filter["order_date_gte"])
            if filter.get("order_date_lte"):
                qs = qs.filter(order_date__lte=filter["order_date_lte"])
            if filter.get("customer_name"):
                qs = qs.filter(customer__name__icontains=filter["customer_name"])
            if filter.get("product_name"):
                qs = qs.filter(products__name__icontains=filter["product_name"]).distinct()
            if filter.get("product_id"):
                qs = qs.filter(products__id=filter["product_id"]).distinct()
        if order_by and order_by in {"order_date", "-order_date", "total_amount", "-total_amount", "created_at", "-created_at"}:
            qs = qs.order_by(order_by)
        return qs

    # simple list resolvers
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
