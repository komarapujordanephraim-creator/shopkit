import secrets
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Product(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])


def _token():
    return secrets.token_urlsafe(16)


class Order(models.Model):
    PENDING, PAID, SHIPPED, CANCELLED = "pending", "paid", "shipped", "cancelled"
    STATUSES = [(PENDING, "Pending"), (PAID, "Paid"), (SHIPPED, "Shipped"), (CANCELLED, "Cancelled")]

    token = models.CharField(max_length=40, unique=True, default=_token, editable=False)
    name = models.CharField(max_length=120)
    email = models.EmailField()
    address = models.TextField()
    status = models.CharField(max_length=12, choices=STATUSES, default=PENDING)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"Order {self.pk}"

    def get_absolute_url(self):
        return reverse("order_detail", args=[self.token])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)  # snapshot at purchase time
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot at purchase time
    quantity = models.PositiveIntegerField()

    @property
    def line_total(self):
        return self.unit_price * self.quantity
