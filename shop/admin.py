from django.contrib import admin

from .models import Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock", "active")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("price", "stock", "active")


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "name", "unit_price", "quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "email", "total", "status", "created")
    list_filter = ("status",)
    readonly_fields = ("token", "total")
    inlines = [ItemInline]
