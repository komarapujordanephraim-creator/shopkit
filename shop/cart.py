"""Session cart. It stores only product ids and quantities. Prices are always
read from the database, so a client can never set its own price."""
from decimal import Decimal

from .models import Product

KEY = "cart"
MAX_QTY = 20


class Cart:
    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(KEY, {})
        self.data = {str(k): int(v) for k, v in raw.items() if str(k).isdigit() and int(v) > 0}

    def _save(self):
        self.session[KEY] = self.data
        self.session.modified = True

    def set(self, product, qty):
        qty = max(0, min(int(qty), MAX_QTY, product.stock))
        if qty == 0:
            self.data.pop(str(product.pk), None)
        else:
            self.data[str(product.pk)] = qty
        self._save()
        return qty

    def add(self, product, qty=1):
        return self.set(product, self.data.get(str(product.pk), 0) + int(qty))

    def clear(self):
        self.data = {}
        self._save()

    def lines(self):
        products = Product.objects.filter(pk__in=self.data.keys(), active=True)
        out = []
        for p in products:
            q = self.data[str(p.pk)]
            out.append({"product": p, "quantity": q, "line_total": p.price * q})
        return out

    def total(self):
        return sum((l["line_total"] for l in self.lines()), Decimal("0.00"))

    def count(self):
        return sum(self.data.values())
