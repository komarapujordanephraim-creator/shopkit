# ShopKit: a small e-commerce store in Django

A compact online store: product catalogue, session cart, checkout, order tracking link and a staff order screen. Built with Django 5 and SQLite. It is a portfolio project that shows how I handle the parts of e-commerce that go wrong most often (prices, stock and order states), not a production shop.

## What it does

- **Catalogue** with search, product pages and out-of-stock handling.
- **Cart** stored in the session. It keeps only product ids and quantities; prices always come from the database, so a customer cannot change the price they pay. Quantities are capped by stock.
- **Checkout** creates the order inside a database transaction and locks the product rows, so two customers cannot both buy the last item. If stock ran out in the meantime, nothing is charged or saved and the customer is sent back to the cart.
- **Price snapshot.** Each order line stores the name and price at the time of purchase, so later price changes do not alter old orders.
- **Order page** reachable only through a secret link (no guessable order numbers).
- **Staff orders screen** with a fixed status flow: Pending, Paid, Shipped, or Cancelled. Cancelling puts the items back in stock, and a cancelled order cannot be cancelled twice.
- **Django admin** for products and orders.

## Run it

```
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo      # 6 fictional products and a staff user (staff / staff12345)
python manage.py runserver
python manage.py test
```

Settings read `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` and `DJANGO_ALLOWED_HOSTS` from the environment. The defaults and the demo staff password are for local development only.

## Tests

16 tests cover database pricing (a posted price is ignored), stock caps, junk and negative quantities, inactive products, POST-only cart changes, order creation with price snapshots and stock reduction, the "stock ran out during checkout" case, invalid forms, the secret order link, staff-only access, cancel-and-restock, double cancel and the status flow. I also removed the stock check and the status rules on purpose to confirm the tests fail.

## Not included (be aware before using it for real)

- **No real payments.** Orders start as Pending (for example pay on delivery). Connect Stripe or Razorpay and mark orders Paid from a webhook.
- **No emails** to the customer, no shipping rates, taxes, coupons or product images (a letter placeholder is shown).
- **No customer accounts**; customers keep their order link.
- SQLite. Use PostgreSQL for real traffic (the row locking is designed for it).

MIT License. Built by Komarapu Jordan Ephraim.
