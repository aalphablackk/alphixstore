from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

    readonly_fields = (
        "product",
        "quantity",
        "price",
        "subtotal",
        "created_at",
    )

    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_number",
        "user",
        "total_amount",
        "status",
        "payment_status",
        "stock_reserved",
        "created_at",
    )

    search_fields = (
        "order_number",
        "user__username",
        "user__email",
        "phone_number",
    )

    list_filter = (
        "status",
        "payment_status",
        "stock_reserved",
        "created_at",
    )

    readonly_fields = (
        "order_number",
        "total_amount",
        "stock_reserved",
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    list_per_page = 25

    inlines = (
        OrderItemInline,
    )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):

    list_display = (
        "order",
        "product",
        "quantity",
        "price",
        "subtotal",
        "created_at",
    )

    search_fields = (
        "order__order_number",
        "product__name",
    )

    list_filter = (
        "created_at",
    )

    readonly_fields = (
        "order",
        "product",
        "quantity",
        "price",
        "subtotal",
        "created_at",
    )

    ordering = (
        "-created_at",
    )