from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from products.models import Category, Brand, Product


class CartTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics"
        )

        self.brand = Brand.objects.create(
            name="Test Brand",
            category=self.category
        )

        self.product = Product.objects.create(
            name="Test Laptop",
            brand=self.brand,
            description="A test laptop.",
            price=Decimal("500000.00"),
            is_in_stock=True,
            quantity=10,
        )

        self.second_product = Product.objects.create(
            name="Test Mouse",
            brand=self.brand,
            description="A test mouse.",
            price=Decimal("15000.00"),
            is_in_stock=True,
            quantity=5,
        )

    # =========================================================
    # CART PAGE
    # =========================================================

    def test_empty_cart(self):
        response = self.client.get(
            reverse("cart")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.context["cart_items"],
            []
        )

        self.assertEqual(
            response.context["cart_total"],
            0
        )


    # =========================================================
    # ADD TO CART
    # =========================================================

    def test_add_product_to_cart(self):
        response = self.client.get(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            1
        )


    def test_add_same_product_increases_quantity(self):
        self.client.get(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        self.client.get(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            2
        )


    def test_cannot_add_more_than_available_stock(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 10
        }

        session.save()

        response = self.client.get(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            10
        )


    def test_cannot_add_out_of_stock_product(self):
        self.product.quantity = 0
        self.product.is_in_stock = False
        self.product.save()

        response = self.client.get(
            reverse(
                "add_to_cart",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session.get(
            "cart",
            {}
        )

        self.assertNotIn(
            str(self.product.id),
            cart
        )


    # =========================================================
    # CART TOTAL
    # =========================================================

    def test_cart_calculates_total(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 2,
            str(self.second_product.id): 3,
        }

        session.save()

        response = self.client.get(
            reverse("cart")
        )

        expected_total = (
            Decimal("500000.00") * 2
            + Decimal("15000.00") * 3
        )

        self.assertEqual(
            response.context["cart_total"],
            expected_total
        )


    # =========================================================
    # CART VIEW STOCK VALIDATION
    # =========================================================

    def test_cart_reduces_quantity_when_above_stock(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 20
        }

        session.save()

        response = self.client.get(
            reverse("cart")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            10
        )


    def test_cart_removes_deleted_product(self):
        product_id = self.product.id

        session = self.client.session

        session["cart"] = {
            str(product_id): 2
        }

        session.save()

        self.product.delete()

        response = self.client.get(
            reverse("cart")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        cart = self.client.session["cart"]

        self.assertNotIn(
            str(product_id),
            cart
        )


    def test_cart_removes_zero_quantity(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 0
        }

        session.save()

        response = self.client.get(
            reverse("cart")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        cart = self.client.session["cart"]

        self.assertNotIn(
            str(self.product.id),
            cart
        )


    def test_cart_removes_negative_quantity(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): -2
        }

        session.save()

        response = self.client.get(
            reverse("cart")
        )

        self.assertEqual(
            response.status_code,
            200
        )

        cart = self.client.session["cart"]

        self.assertNotIn(
            str(self.product.id),
            cart
        )


    # =========================================================
    # UPDATE CART
    # =========================================================

    def test_update_cart_quantity(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 1
        }

        session.save()

        response = self.client.post(
            reverse(
                "update_cart",
                args=[self.product.id]
            ),
            {
                "quantity": 5
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            5
        )


    def test_update_cart_cannot_exceed_stock(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 1
        }

        session.save()

        response = self.client.post(
            reverse(
                "update_cart",
                args=[self.product.id]
            ),
            {
                "quantity": 50
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            10
        )


    def test_update_cart_zero_removes_product(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 3
        }

        session.save()

        response = self.client.post(
            reverse(
                "update_cart",
                args=[self.product.id]
            ),
            {
                "quantity": 0
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertNotIn(
            str(self.product.id),
            cart
        )


    def test_update_cart_negative_quantity_removes_product(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 3
        }

        session.save()

        response = self.client.post(
            reverse(
                "update_cart",
                args=[self.product.id]
            ),
            {
                "quantity": -5
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertNotIn(
            str(self.product.id),
            cart
        )


    def test_update_cart_invalid_quantity(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 3
        }

        session.save()

        response = self.client.post(
            reverse(
                "update_cart",
                args=[self.product.id]
            ),
            {
                "quantity": "invalid"
            }
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            3
        )


    def test_update_cart_requires_post(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 3
        }

        session.save()

        response = self.client.get(
            reverse(
                "update_cart",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            3
        )


    # =========================================================
    # REMOVE FROM CART
    # =========================================================

    def test_remove_product_from_cart(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 2,
            str(self.second_product.id): 1,
        }

        session.save()

        response = self.client.post(
            reverse(
                "remove_from_cart",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertNotIn(
            str(self.product.id),
            cart
        )

        self.assertEqual(
            cart[str(self.second_product.id)],
            1
        )


    def test_remove_from_cart_requires_post(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 2
        }

        session.save()

        response = self.client.get(
            reverse(
                "remove_from_cart",
                args=[self.product.id]
            )
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            2
        )


    # =========================================================
    # CLEAR CART
    # =========================================================

    def test_clear_cart(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 2,
            str(self.second_product.id): 1,
        }

        session.save()

        response = self.client.post(
            reverse("clear_cart")
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart,
            {}
        )


    def test_clear_cart_requires_post(self):
        session = self.client.session

        session["cart"] = {
            str(self.product.id): 2
        }

        session.save()

        response = self.client.get(
            reverse("clear_cart")
        )

        self.assertRedirects(
            response,
            reverse("cart")
        )

        cart = self.client.session["cart"]

        self.assertEqual(
            cart[str(self.product.id)],
            2
        )