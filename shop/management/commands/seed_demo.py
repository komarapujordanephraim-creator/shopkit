from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from shop.models import Product

PRODUCTS = [
    ("Ceramic Coffee Mug", "ceramic-coffee-mug", "350 ml stoneware mug.", "12.00", 25),
    ("Canvas Tote Bag", "canvas-tote-bag", "Heavy cotton tote with inner pocket.", "18.50", 40),
    ("Notebook A5 Dotted", "notebook-a5-dotted", "120 pages, lay-flat binding.", "9.90", 60),
    ("Desk Plant (Small)", "desk-plant-small", "Low-light plant in a 10 cm pot.", "15.00", 8),
    ("Wireless Mouse", "wireless-mouse", "Quiet clicks, USB receiver.", "24.00", 3),
    ("Bamboo Pen Set", "bamboo-pen-set", "Set of 3 refillable pens.", "7.50", 0),
]


class Command(BaseCommand):
    help = "Create fictional demo products and a staff user (staff / staff12345)."

    def handle(self, *args, **opts):
        for name, slug, desc, price, stock in PRODUCTS:
            Product.objects.update_or_create(slug=slug, defaults={
                "name": name, "description": desc, "price": Decimal(price), "stock": stock, "active": True})
        User = get_user_model()
        if not User.objects.filter(username="staff").exists():
            User.objects.create_user("staff", "staff@example.com", "staff12345", is_staff=True, is_superuser=True)
        if opts.get("verbosity", 1):
            self.stdout.write(self.style.SUCCESS(f"{len(PRODUCTS)} demo products ready. Staff login: staff / staff12345"))
