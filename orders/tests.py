from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from products.models import Category, Brand, Product

from .models import Order, OrderItem
from .services import (
    reserve_order_stock,
    release_order_stock,
    cancel_order_and_restore_stock,
)


class OrderModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="orderuser",
            email="order@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Electronics"
        )

        self.brand = Brand.objects.create(
            name="Order Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Test Phone",
            brand=self.brand,
            description="A test phone.",
            price=Decimal("300000.00"),
            is_in_stock=True,
            quantity=10,
        )

    def create_order(
        self,
        quantity=2,
        stock_reserved=True,
    ):
        order = Order.objects.create(
            user=self.user,
            total_amount=(
                self.product.price * quantity
            ),
            shipping_address="Lagos, Nigeria",
            phone_number="08012345678",
            stock_reserved=stock_reserved,
        )

        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=quantity,
            price=self.product.price,
            subtotal=(
                self.product.price * quantity
            ),
        )

        return order


    def test_order_number_generated_automatically(self):
        order = self.create_order()

        self.assertTrue(
            order.order_number.startswith("ALPX-")
        )

        self.assertEqual(
            len(order.order_number),
            15,
        )


    def test_order_defaults(self):
        order = self.create_order()

        self.assertEqual(
            order.status,
            "PENDING",
        )

        self.assertEqual(
            order.payment_status,
            "PENDING",
        )

        self.assertTrue(
            order.stock_reserved,
        )


    def test_order_item_relationship(self):
        order = self.create_order(
            quantity=3
        )

        self.assertEqual(
            order.items.count(),
            1,
        )

        item = order.items.first()

        self.assertEqual(
            item.product,
            self.product,
        )

        self.assertEqual(
            item.quantity,
            3,
        )

        self.assertEqual(
            item.price,
            Decimal("300000.00"),
        )

        self.assertEqual(
            item.subtotal,
            Decimal("900000.00"),
        )


class OrderStockServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="stockuser",
            email="stock@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Stock Category"
        )

        self.brand = Brand.objects.create(
            name="Stock Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Stock Product",
            brand=self.brand,
            description="A stock test product.",
            price=Decimal("100000.00"),
            is_in_stock=True,
            quantity=10,
        )


    def create_order(
        self,
        quantity=2,
        stock_reserved=False,
    ):
        order = Order.objects.create(
            user=self.user,
            total_amount=(
                self.product.price * quantity
            ),
            shipping_address="Lagos, Nigeria",
            phone_number="08012345678",
            stock_reserved=stock_reserved,
        )

        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=quantity,
            price=self.product.price,
            subtotal=(
                self.product.price * quantity
            ),
        )

        return order


    # =========================================================
    # RESERVE STOCK
    # =========================================================

    def test_reserve_order_stock(self):
        order = self.create_order(
            quantity=3,
            stock_reserved=False,
        )

        result = reserve_order_stock(order)

        self.assertTrue(result)

        self.product.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            7,
        )

        self.assertTrue(
            self.product.is_in_stock,
        )

        self.assertTrue(
            order.stock_reserved,
        )


    def test_reserve_order_stock_when_already_reserved(self):
        order = self.create_order(
            quantity=3,
            stock_reserved=True,
        )

        original_quantity = self.product.quantity

        result = reserve_order_stock(order)

        self.assertFalse(result)

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            original_quantity,
        )


    def test_reserve_order_stock_rejects_insufficient_stock(self):
        order = self.create_order(
            quantity=20,
            stock_reserved=False,
        )

        with self.assertRaises(ValueError):
            reserve_order_stock(order)

        self.product.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            10,
        )

        self.assertTrue(
            self.product.is_in_stock,
        )

        self.assertFalse(
            order.stock_reserved,
        )


    def test_reserve_order_stock_sets_out_of_stock_when_quantity_reaches_zero(self):
        order = self.create_order(
            quantity=10,
            stock_reserved=False,
        )

        result = reserve_order_stock(order)

        self.assertTrue(result)

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            0,
        )

        self.assertFalse(
            self.product.is_in_stock,
        )


    # =========================================================
    # RELEASE STOCK
    # =========================================================

    def test_release_order_stock(self):
        order = self.create_order(
            quantity=3,
            stock_reserved=True,
        )

        self.product.quantity = 7
        self.product.is_in_stock = True
        self.product.save()

        result = release_order_stock(order)

        self.assertTrue(result)

        self.product.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            10,
        )

        self.assertTrue(
            self.product.is_in_stock,
        )

        self.assertFalse(
            order.stock_reserved,
        )


    def test_release_order_stock_when_already_released(self):
        order = self.create_order(
            quantity=3,
            stock_reserved=False,
        )

        original_quantity = self.product.quantity

        result = release_order_stock(order)

        self.assertFalse(result)

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            original_quantity,
        )


    # =========================================================
    # CANCEL ORDER
    # =========================================================

    def test_cancel_order_restores_stock(self):
        order = self.create_order(
            quantity=3,
            stock_reserved=True,
        )

        self.product.quantity = 7
        self.product.is_in_stock = True
        self.product.save()

        result = cancel_order_and_restore_stock(
            order
        )

        self.assertTrue(result)

        self.product.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(
            order.status,
            "CANCELLED",
        )

        self.assertFalse(
            order.stock_reserved,
        )

        self.assertEqual(
            self.product.quantity,
            10,
        )

        self.assertTrue(
            self.product.is_in_stock,
        )


    def test_cancelled_order_cannot_be_cancelled_twice(self):
        order = self.create_order(
            quantity=3,
            stock_reserved=True,
        )

        self.product.quantity = 7
        self.product.is_in_stock = True
        self.product.save()

        first_result = cancel_order_and_restore_stock(
            order
        )

        self.assertTrue(first_result)

        self.product.refresh_from_db()

        quantity_after_first_cancel = (
            self.product.quantity
        )

        second_result = cancel_order_and_restore_stock(
            order
        )

        self.assertFalse(second_result)

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            quantity_after_first_cancel,
        )


    def test_cancel_order_releases_stock_reservation(self):
        order = self.create_order(
            quantity=2,
            stock_reserved=True,
        )

        self.product.quantity = 8
        self.product.is_in_stock = True
        self.product.save()

        cancel_order_and_restore_stock(
            order
        )

        order.refresh_from_db()

        self.assertFalse(
            order.stock_reserved
        )

        self.assertEqual(
            order.status,
            "CANCELLED"
        )


# =========================================================
# CHECKOUT VIEW
# =========================================================

from django.urls import reverse


class CheckoutViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="checkoutuser",
            email="checkout@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Checkout Category"
        )

        self.brand = Brand.objects.create(
            name="Checkout Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Checkout Product",
            brand=self.brand,
            description="A checkout test product.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

        self.checkout_url = reverse("checkout")

    def login(self):
        self.client.login(
            username="checkoutuser",
            password="TestPassword123!",
        )

    def add_product_to_cart(self, quantity=1):
        session = self.client.session
        session["cart"] = {
            str(self.product.id): quantity
        }
        session.save()

    # ---------------------------------------------------------
    # AUTHENTICATION
    # ---------------------------------------------------------

    def test_checkout_requires_login(self):
        response = self.client.get(self.checkout_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    # ---------------------------------------------------------
    # EMPTY CART
    # ---------------------------------------------------------

    def test_checkout_with_empty_cart_does_not_create_order(self):
        self.login()

        response = self.client.get(self.checkout_url)

        self.assertEqual(Order.objects.count(), 0)

    # ---------------------------------------------------------
    # CHECKOUT PAGE
    # ---------------------------------------------------------

    def test_checkout_page_loads_with_products_in_cart(self):
        self.login()
        self.add_product_to_cart(quantity=2)

        response = self.client.get(self.checkout_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "orders/checkout.html")

    # ---------------------------------------------------------
    # SUCCESSFUL CHECKOUT
    # ---------------------------------------------------------

    def test_successful_checkout_creates_order(self):
        self.login()
        self.add_product_to_cart(quantity=2)

        response = self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )

        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.first()

        self.assertEqual(order.user, self.user)
        self.assertEqual(
            order.shipping_address,
            "123 Lagos Street, Lagos",
        )
        self.assertEqual(
            order.phone_number,
            "08012345678",
        )

    def test_successful_checkout_creates_order_item(self):
        self.login()
        self.add_product_to_cart(quantity=2)

        self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )

        order = Order.objects.first()

        self.assertEqual(order.items.count(), 1)

        item = order.items.first()

        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(
            item.price,
            Decimal("50000.00"),
        )
        self.assertEqual(
            item.subtotal,
            Decimal("100000.00"),
        )

    def test_checkout_calculates_correct_order_total(self):
        self.login()
        self.add_product_to_cart(quantity=3)

        self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )

        order = Order.objects.first()

        self.assertEqual(
            order.total_amount,
            Decimal("150000.00"),
        )

    # ---------------------------------------------------------
    # STOCK
    # ---------------------------------------------------------

    def test_successful_checkout_reduces_product_stock(self):
        self.login()
        self.add_product_to_cart(quantity=3)

        self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            7,
        )

        self.assertTrue(
            self.product.is_in_stock,
        )

    def test_checkout_sets_product_out_of_stock_when_stock_reaches_zero(self):
        self.login()
        self.add_product_to_cart(quantity=10)

        self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            0,
        )

        self.assertFalse(
            self.product.is_in_stock,
        )

    # ---------------------------------------------------------
    # CART
    # ---------------------------------------------------------

    def test_successful_checkout_clears_cart(self):
        self.login()
        self.add_product_to_cart(quantity=2)

        response = self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )
        self.assertEqual(
            self.client.session.get("cart"),
            {},
        )


        
    # ---------------------------------------------------------
    # INSUFFICIENT STOCK
    # ---------------------------------------------------------

    def test_checkout_does_not_create_order_when_stock_is_insufficient(self):
        self.login()
        self.add_product_to_cart(quantity=15)

        response = self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )

        self.assertEqual(
            Order.objects.count(),
            0,
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.quantity,
            10,
        )

    def test_checkout_does_not_clear_cart_when_stock_is_insufficient(self):
        self.login()
        self.add_product_to_cart(quantity=15)

        self.client.post(
            self.checkout_url,
            {
                "shipping_address": "123 Lagos Street, Lagos",
                "phone_number": "08012345678",
            },
        )

        session = self.client.session

        self.assertIn(
            "cart",
            session,
        )

        self.assertEqual(
            session["cart"][str(self.product.id)],
            15,
        )