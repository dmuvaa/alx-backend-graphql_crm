# crm/filters.py
import django_filters as df
from .models import Customer, Product, Order

class CustomerFilter(df.FilterSet):
    name = df.CharFilter(field_name="name", lookup_expr="icontains")
    email = df.CharFilter(field_name="email", lookup_expr="icontains")
    created_at__gte = df.DateFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = df.DateFilter(field_name="created_at", lookup_expr="lte")

    # Challenge: phone number pattern (e.g., starts with "+1")
    phone_pattern = df.CharFilter(method="filter_phone_pattern")

    def filter_phone_pattern(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(phone__startswith=value)

    class Meta:
        model = Customer
        fields = ["name", "email", "created_at__gte", "created_at__lte"]

class ProductFilter(df.FilterSet):
    name = df.CharFilter(field_name="name", lookup_expr="icontains")
    price__gte = df.NumberFilter(field_name="price", lookup_expr="gte")
    price__lte = df.NumberFilter(field_name="price", lookup_expr="lte")
    stock__gte = df.NumberFilter(field_name="stock", lookup_expr="gte")
    stock__lte = df.NumberFilter(field_name="stock", lookup_expr="lte")

    # Convenience: low stock (stock < 10)
    low_stock = df.BooleanFilter(method="filter_low_stock")

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__lt=10)
        return queryset

    class Meta:
        model = Product
        fields = ["name", "price__gte", "price__lte", "stock__gte", "stock__lte"]

class OrderFilter(df.FilterSet):
    total_amount__gte = df.NumberFilter(field_name="total_amount", lookup_expr="gte")
    total_amount__lte = df.NumberFilter(field_name="total_amount", lookup_expr="lte")
    order_date__gte = df.DateTimeFilter(field_name="order_date", lookup_expr="gte")
    order_date__lte = df.DateTimeFilter(field_name="order_date", lookup_expr="lte")

    customer_name = df.CharFilter(method="filter_customer_name")
    product_name = df.CharFilter(method="filter_product_name")
    product_id = df.CharFilter(method="filter_product_id")  # challenge

    def filter_customer_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(customer__name__icontains=value)

    def filter_product_name(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(products__name__icontains=value).distinct()

    def filter_product_id(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(products__id=value).distinct()

    class Meta:
        model = Order
        fields = ["total_amount__gte", "total_amount__lte", "order_date__gte", "order_date__lte"]
