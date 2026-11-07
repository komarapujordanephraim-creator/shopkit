from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Order, Product


def product(slug, price="10.00", stock=5, active=True):
    return Product.objects.create(name=slug.title(), slug=slug, price=Decimal(price), stock=stock, active=active)


CUSTOMER = {"name": "Test Buyer", "email": "buyer@example.com", "address": "1 Test Street"}


class CartTests(TestCase):
    def setUp(self):
        self.mug = product("mug", "12.00", stock=3)

    def test_add_and_total_use_database_price(self):
        self.client.post(reverse("cart_add", args=[self.mug.pk]), {"quantity": 2, "price": "0.01"})
        r = self.client.get(reverse("cart_detail"))
        self.assertEqual(r.context["total"], Decimal("24.00"))

    def test_cannot_add_more_than_stock(self):
        self.client.post(reverse("cart_add", args=[self.mug.pk]), {"quantity": 10})
        self.assertEqual(self.client.session["cart"][str(self.mug.pk)], 3)

    def test_update_to_zero_removes_item(self):
        self.client.post(reverse("cart_add", args=[self.mug.pk]))
        self.client.post(reverse("cart_update", args=[self.mug.pk]), {"quantity": 0})
        self.assertNotIn(str(self.mug.pk), self.client.session["cart"])

    def test_negative_or_junk_quantity_is_safe(self):
        self.client.post(reverse("cart_add", args=[self.mug.pk]))
        self.client.post(reverse("cart_update", args=[self.mug.pk]), {"quantity": "-5"})
        self.assertNotIn(str(self.mug.pk), self.client.session["cart"])
        self.client.post(reverse("cart_update", args=[self.mug.pk]), {"quantity": "abc"})
        self.assertEqual(self.client.get(reverse("cart_detail")).status_code, 200)

    def test_inactive_product_cannot_be_added_or_viewed(self):
        hidden = product("hidden", active=False)
        self.assertEqual(self.client.post(reverse("cart_add", args=[hidden.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("product_detail", args=["hidden"])).status_code, 404)

    def test_add_requires_post(self):
        self.assertEqual(self.client.get(reverse("cart_add", args=[self.mug.pk])).status_code, 405)


class CheckoutTests(TestCase):
    def setUp(self):
        self.mug = product("mug", "12.00", stock=3)
        self.bag = product("bag", "18.50", stock=10)

    def _cart(self, *items):
        for p, q in items:
            self.client.post(reverse("cart_add", args=[p.pk]), {"quantity": q})

    def test_checkout_creates_order_snapshots_prices_and_reduces_stock(self):
        self._cart((self.mug, 2), (self.bag, 1))
        r = self.client.post(reverse("checkout"), CUSTOMER)
        order = Order.objects.get()
        self.assertRedirects(r, order.get_absolute_url())
        self.assertEqual(order.total, Decimal("42.50"))
        self.mug.refresh_from_db()
        self.assertEqual(self.mug.stock, 1)
        # A later price change must not change the order.
        Product.objects.filter(pk=self.mug.pk).update(price=Decimal("99.00"))
        item = order.items.get(product=self.mug)
        self.assertEqual(item.unit_price, Decimal("12.00"))
        self.assertEqual(self.client.session.get("cart"), {})

    def test_checkout_fails_cleanly_if_stock_ran_out(self):
        self._cart((self.mug, 3))
        Product.objects.filter(pk=self.mug.pk).update(stock=1)  # someone else bought them
        r = self.client.post(reverse("checkout"), CUSTOMER)
        self.assertRedirects(r, reverse("cart_detail"))
        self.assertEqual(Order.objects.count(), 0)
        self.mug.refresh_from_db()
        self.assertEqual(self.mug.stock, 1)

    def test_invalid_form_creates_nothing(self):
        self._cart((self.mug, 1))
        r = self.client.post(reverse("checkout"), {"name": "", "email": "bad", "address": ""})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_empty_cart_redirects(self):
        self.assertRedirects(self.client.get(reverse("checkout")), reverse("product_list"))

    def test_order_page_needs_the_secret_token(self):
        self._cart((self.mug, 1))
        self.client.post(reverse("checkout"), CUSTOMER)
        order = Order.objects.get()
        self.assertEqual(self.client.get(reverse("order_detail", args=["guess"])).status_code, 404)
        self.assertContains(self.client.get(order.get_absolute_url()), "Test Buyer")


class StaffTests(TestCase):
    def setUp(self):
        self.mug = product("mug", "12.00", stock=5)
        self.client.post(reverse("cart_add", args=[self.mug.pk]), {"quantity": 2})
        self.client.post(reverse("checkout"), CUSTOMER)
        self.order = Order.objects.get()
        self.staff = get_user_model().objects.create_user("staff", "s@example.com", "pw-12345-test", is_staff=True)

    def test_customers_cannot_see_staff_pages(self):
        r = self.client.get(reverse("staff_orders"))
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse("staff_set_status", args=[self.order.pk]), {"status": "paid"})
        self.assertEqual(r.status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")

    def test_cancel_restocks(self):
        self.client.force_login(self.staff)
        self.client.post(reverse("staff_set_status", args=[self.order.pk]), {"status": "cancelled"})
        self.mug.refresh_from_db()
        self.assertEqual(self.mug.stock, 5)

    def test_cancelled_order_cannot_be_cancelled_again(self):
        self.client.force_login(self.staff)
        self.client.post(reverse("staff_set_status", args=[self.order.pk]), {"status": "cancelled"})
        self.client.post(reverse("staff_set_status", args=[self.order.pk]), {"status": "cancelled"})
        self.mug.refresh_from_db()
        self.assertEqual(self.mug.stock, 5)

    def test_status_flow(self):
        self.client.force_login(self.staff)
        self.client.post(reverse("staff_set_status", args=[self.order.pk]), {"status": "shipped"})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "pending")  # must be paid first
        for s in ("paid", "shipped"):
            self.client.post(reverse("staff_set_status", args=[self.order.pk]), {"status": s})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, "shipped")


class SeedTests(TestCase):
    def test_seed_demo_runs_twice(self):
        from django.core.management import call_command
        call_command("seed_demo", verbosity=0)
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Product.objects.count(), 6)
