from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm
from .models import Order, OrderItem, Product


def product_list(request):
    q = request.GET.get("q", "").strip()
    products = Product.objects.filter(active=True)
    if q:
        products = products.filter(name__icontains=q)
    return render(request, "shop/product_list.html", {"products": products, "q": q})


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, active=True)
    return render(request, "shop/product_detail.html", {"product": product})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    cart = Cart(request)
    before = cart.data.get(str(pk), 0)
    after = cart.add(product, request.POST.get("quantity", 1) or 1)
    if after == before:
        messages.error(request, f"Only {product.stock} of {product.name} in stock.")
    else:
        messages.success(request, f"Added {product.name} to your cart.")
    return redirect("cart_detail")


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        qty = int(request.POST.get("quantity", 0))
    except ValueError:
        qty = 0
    Cart(request).set(product, qty)
    return redirect("cart_detail")


def cart_detail(request):
    cart = Cart(request)
    return render(request, "shop/cart.html", {"lines": cart.lines(), "total": cart.total()})


class OutOfStock(Exception):
    pass


def checkout(request):
    cart = Cart(request)
    lines = cart.lines()
    if not lines:
        messages.info(request, "Your cart is empty.")
        return redirect("product_list")
    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                ids = [l["product"].pk for l in lines]
                # Lock the product rows so two buyers cannot take the same last item.
                locked = {p.pk: p for p in Product.objects.select_for_update().filter(pk__in=ids, active=True)}
                total = 0
                items = []
                for l in lines:
                    p = locked.get(l["product"].pk)
                    if p is None or p.stock < l["quantity"]:
                        raise OutOfStock(l["product"].name)
                    items.append((p, l["quantity"]))
                    total += p.price * l["quantity"]
                order = Order.objects.create(total=total, **form.cleaned_data)
                for p, qty in items:
                    OrderItem.objects.create(order=order, product=p, name=p.name, unit_price=p.price, quantity=qty)
                    Product.objects.filter(pk=p.pk).update(stock=F("stock") - qty)
        except OutOfStock as e:
            messages.error(request, f"Sorry, {e} no longer has enough stock. Please update your cart.")
            return redirect("cart_detail")
        cart.clear()
        return redirect(order)
    return render(request, "shop/checkout.html", {"form": form, "lines": lines, "total": cart.total()})


def order_detail(request, token):
    order = get_object_or_404(Order.objects.prefetch_related("items"), token=token)
    return render(request, "shop/order_detail.html", {"order": order})


@staff_member_required
def staff_orders(request):
    status = request.GET.get("status", "")
    orders = Order.objects.prefetch_related("items")
    if status in dict(Order.STATUSES):
        orders = orders.filter(status=status)
    return render(request, "shop/staff_orders.html", {"orders": orders, "statuses": Order.STATUSES, "current": status})


ALLOWED = {
    Order.PENDING: {Order.PAID, Order.CANCELLED},
    Order.PAID: {Order.SHIPPED, Order.CANCELLED},
    Order.SHIPPED: set(),
    Order.CANCELLED: set(),
}


@staff_member_required
@require_POST
def staff_set_status(request, pk):
    new = request.POST.get("status")
    with transaction.atomic():
        order = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        if new not in ALLOWED[order.status]:
            messages.error(request, f"Cannot change order {order.pk} from {order.get_status_display()} to {new}.")
            return redirect("staff_orders")
        if new == Order.CANCELLED:  # put the items back on the shelf
            for item in order.items.all():
                Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)
        order.status = new
        order.save(update_fields=["status"])
    messages.success(request, f"Order {order.pk} is now {order.get_status_display()}.")
    return redirect("staff_orders")
