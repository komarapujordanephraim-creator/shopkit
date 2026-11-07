from django.urls import path

from . import views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("p/<slug:slug>/", views.product_detail, name="product_detail"),
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/<str:token>/", views.order_detail, name="order_detail"),
    path("staff/orders/", views.staff_orders, name="staff_orders"),
    path("staff/orders/<int:pk>/status/", views.staff_set_status, name="staff_set_status"),
]
