from django.db import transaction

from .models import Order
from products.models import Product


def _release_order_stock_locked(order):
    """
    Internal helper.

    Assumes the order is already locked inside a transaction.
    Prevents the same order's stock from being released twice.
    """

    if not order.stock_reserved:
        return False

    items = order.items.select_related("product")

    for item in items:
        product = (
            Product.objects
            .select_for_update()
            .get(pk=item.product_id)
        )

        product.quantity += item.quantity
        product.is_in_stock = product.quantity > 0

        product.save(
            update_fields=[
                "quantity",
                "is_in_stock",
                "updated_at",
            ]
        )

    order.stock_reserved = False

    order.save(
        update_fields=[
            "stock_reserved",
            "updated_at",
        ]
    )

    return True


def release_order_stock(order):
    """
    Release stock reserved by an unpaid order.

    This does NOT cancel the order.
    It only returns the reserved quantities to inventory.

    Safe to call multiple times.
    """

    with transaction.atomic():

        order = (
            Order.objects
            .select_for_update()
            .get(pk=order.pk)
        )

        return _release_order_stock_locked(order)


def reserve_order_stock(order):
    """
    Reserve stock for an unpaid order.

    Used when retrying payment after stock was previously released.

    Safe to call multiple times.
    """

    with transaction.atomic():

        order = (
            Order.objects
            .select_for_update()
            .get(pk=order.pk)
        )

        # Stock is already reserved for this order.
        if order.stock_reserved:
            return False

        items = order.items.select_related("product")

        for item in items:

            product = (
                Product.objects
                .select_for_update()
                .get(pk=item.product_id)
            )

            if (
                not product.is_in_stock
                or product.quantity < item.quantity
            ):
                raise ValueError(
                    f"Only {product.quantity} unit(s) "
                    f"of {product.name} are available."
                )

            product.quantity -= item.quantity

            product.is_in_stock = product.quantity > 0

            product.save(
                update_fields=[
                    "quantity",
                    "is_in_stock",
                    "updated_at",
                ]
            )

        order.stock_reserved = True

        order.save(
            update_fields=[
                "stock_reserved",
                "updated_at",
            ]
        )

        return True


def cancel_order_and_restore_stock(order):
    """
    Cancel an order and restore its reserved stock.

    Stock is restored only if the order currently
    has stock reserved.
    """

    with transaction.atomic():

        order = (
            Order.objects
            .select_for_update()
            .get(pk=order.pk)
        )

        if order.status == "CANCELLED":
            return False

        _release_order_stock_locked(order)

        order.status = "CANCELLED"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

        return True