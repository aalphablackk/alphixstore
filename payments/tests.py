from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order, OrderItem
from products.models import Category, Brand, Product

from .models import Payment
from .services import (
    confirm_payment,
    fail_payment,
    generate_payment_reference,
    initialize_payment,
)


class PaymentTestMixin:

    def create_payment_order(
        self,
        quantity=2,
        stock_reserved=True,
    ):
        order = Order.objects.create(
            user=self.user,
            total_amount=self.product.price * quantity,
            shipping_address="Lagos, Nigeria",
            phone_number="08012345678",
            stock_reserved=stock_reserved,
        )

        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=quantity,
            price=self.product.price,
            subtotal=self.product.price * quantity,
        )

        return order


class PaymentModelTests(PaymentTestMixin, TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="paymentuser",
            email="payment@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Payment Category",
        )

        self.brand = Brand.objects.create(
            name="Payment Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Payment Product",
            brand=self.brand,
            description="A payment test product.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

    def test_payment_creation(self):
        order = self.create_payment_order()

        payment = Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-TEST123456",
            amount=Decimal("100000.00"),
            currency="NGN",
            provider=Payment.Provider.PAYSTACK,
        )

        self.assertEqual(payment.order, order)
        self.assertEqual(
            payment.amount,
            Decimal("100000.00"),
        )
        self.assertEqual(
            payment.currency,
            "NGN",
        )
        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )
        self.assertEqual(
            payment.provider,
            Payment.Provider.PAYSTACK,
        )

    def test_payment_string_representation(self):
        order = self.create_payment_order()

        payment = Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-TEST123456",
            amount=Decimal("100000.00"),
        )

        self.assertEqual(
            str(payment),
            "ALPHIX-TEST123456",
        )

    def test_payment_reference_is_unique(self):
        order = self.create_payment_order()

        Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-DUPLICATE",
            amount=Decimal("100000.00"),
        )

        with self.assertRaises(Exception):
            Payment.objects.create(
                order=order,
                payment_reference="ALPHIX-DUPLICATE",
                amount=Decimal("100000.00"),
            )


class PaymentServiceTests(PaymentTestMixin, TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="serviceuser",
            email="service@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Service Category",
        )

        self.brand = Brand.objects.create(
            name="Service Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Service Product",
            brand=self.brand,
            description="A payment service test product.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

    def test_generate_payment_reference(self):
        reference = generate_payment_reference()

        self.assertTrue(
            reference.startswith("ALPHIX-")
        )

        self.assertEqual(
            len(reference),
            19,
        )

    @patch("payments.services.initialize_transaction")
    def test_initialize_payment_creates_pending_payment(
        self,
        mock_initialize,
    ):
        order = self.create_payment_order()

        mock_initialize.return_value = {
            "authorization_url": (
                "https://checkout.paystack.com/test"
            ),
            "access_code": "test-access-code",
            "reference": "paystack-reference",
        }

        request = self.client.get("/").wsgi_request

        payment, response = initialize_payment(
            order=order,
            request=request,
        )

        self.assertEqual(
            payment.status,
            Payment.Status.PENDING,
        )

        self.assertEqual(
            payment.amount,
            order.total_amount,
        )

        self.assertEqual(
            payment.currency,
            "NGN",
        )

        self.assertEqual(
            payment.provider,
            Payment.Provider.PAYSTACK,
        )

        self.assertEqual(
            response["authorization_url"],
            "https://checkout.paystack.com/test",
        )

        mock_initialize.assert_called_once()

    @patch("payments.services.initialize_transaction")
    def test_initialize_payment_marks_failed_when_paystack_fails(
        self,
        mock_initialize,
    ):
        order = self.create_payment_order()

        mock_initialize.side_effect = Exception(
            "Paystack unavailable"
        )

        request = self.client.get("/").wsgi_request

        with self.assertRaises(Exception):
            initialize_payment(
                order=order,
                request=request,
            )

        payment = Payment.objects.get(
            order=order
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

    @patch("payments.services.initialize_transaction")
    def test_initialize_payment_rejects_missing_authorization_url(
        self,
        mock_initialize,
    ):
        order = self.create_payment_order()

        mock_initialize.return_value = {
            "reference": "paystack-reference",
        }

        request = self.client.get("/").wsgi_request

        with self.assertRaises(ValueError):
            initialize_payment(
                order=order,
                request=request,
            )

        payment = Payment.objects.get(
            order=order
        )

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

    def test_fail_payment(self):
        order = self.create_payment_order(
            quantity=2,
            stock_reserved=True,
        )

        self.product.quantity = 8
        self.product.is_in_stock = True
        self.product.save()

        payment = Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-FAIL123456",
            amount=Decimal("100000.00"),
            status=Payment.Status.PENDING,
        )

        result = fail_payment(payment)

        self.assertTrue(result)

        payment.refresh_from_db()
        order.refresh_from_db()
        self.product.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            order.payment_status,
            "FAILED",
        )

        self.assertFalse(
            order.stock_reserved,
        )

        self.assertEqual(
            self.product.quantity,
            10,
        )

    def test_fail_payment_cannot_process_twice(self):
        order = self.create_payment_order(
            quantity=2,
            stock_reserved=True,
        )

        self.product.quantity = 8
        self.product.save()

        payment = Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-FAILTWICE",
            amount=Decimal("100000.00"),
        )

        first_result = fail_payment(payment)
        second_result = fail_payment(payment)

        self.assertTrue(first_result)
        self.assertFalse(second_result)

    def test_confirm_payment(self):
        order = self.create_payment_order(
            quantity=2,
            stock_reserved=True,
        )

        payment = Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-CONFIRM123",
            amount=Decimal("100000.00"),
            status=Payment.Status.PENDING,
        )

        transaction_data = {
            "id": 123456789,
            "reference": payment.payment_reference,
            "status": "success",
            "currency": "NGN",
            "requested_amount": 10000000,
        }

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            result = confirm_payment(
                payment=payment,
                transaction_data=transaction_data,
            )

        payment.refresh_from_db()
        order.refresh_from_db()

        self.assertTrue(result)

        self.assertEqual(
            payment.status,
            Payment.Status.SUCCESSFUL,
        )

        self.assertEqual(
            payment.transaction_reference,
            "123456789",
        )

        self.assertEqual(
            order.payment_status,
            "PAID",
        )

        self.assertEqual(
            order.status,
            "PROCESSING",
        )

    def test_confirm_payment_cannot_confirm_failed_payment(self):
        order = self.create_payment_order()

        payment = Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-FAILED123",
            amount=Decimal("100000.00"),
            status=Payment.Status.FAILED,
        )

        result = confirm_payment(
            payment=payment,
            transaction_data={
                "id": 123,
                "status": "success",
            },
        )

        self.assertFalse(result)

        payment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.FAILED,
        )

    def test_confirm_payment_is_idempotent(self):
        order = self.create_payment_order()

        payment = Payment.objects.create(
            order=order,
            payment_reference="ALPHIX-IDEMPOTENT",
            amount=Decimal("100000.00"),
            status=Payment.Status.SUCCESSFUL,
            transaction_reference="12345",
        )

        result = confirm_payment(
            payment=payment,
            transaction_data={
                "id": 99999,
                "status": "success",
            },
        )

        self.assertTrue(result)

        payment.refresh_from_db()

        self.assertEqual(
            payment.transaction_reference,
            "12345",
        )


class PaymentCallbackTests(PaymentTestMixin, TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="callbackuser",
            email="callback@example.com",
            password="TestPassword123!",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Callback Category",
        )

        self.brand = Brand.objects.create(
            name="Callback Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Callback Product",
            brand=self.brand,
            description="Callback test product.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

        self.order = self.create_payment_order(
            quantity=2,
            stock_reserved=True,
        )

        self.payment = Payment.objects.create(
            order=self.order,
            payment_reference="ALPHIX-CALLBACK1",
            amount=Decimal("100000.00"),
            status=Payment.Status.PENDING,
        )

        self.callback_url = reverse(
            "payment_callback"
        )

    def login(self):
        self.client.login(
            username="callbackuser",
            password="TestPassword123!",
        )

    def valid_transaction_data(self):
        return {
            "id": 123456789,
            "reference": self.payment.payment_reference,
            "status": "success",
            "currency": "NGN",
            "requested_amount": 10000000,
        }

    def test_callback_requires_login(self):
        response = self.client.get(
            self.callback_url,
            {"reference": self.payment.payment_reference},
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            "/accounts/login/",
            response.url,
        )

    def test_callback_requires_reference(self):
        self.login()

        response = self.client.get(
            self.callback_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("my_orders"),
        )

    @patch("payments.views.verify_transaction")
    def test_successful_callback_confirms_payment(
        self,
        mock_verify,
    ):
        self.login()

        mock_verify.return_value = (
            self.valid_transaction_data()
        )

        with self.captureOnCommitCallbacks(
            execute=True
        ):
            response = self.client.get(
                self.callback_url,
                {
                    "reference":
                        self.payment.payment_reference
                },
            )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            self.order.order_number,
            response.url,
        )

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCESSFUL,
        )

        self.assertEqual(
            self.order.payment_status,
            "PAID",
        )

        self.assertEqual(
            self.order.status,
            "PROCESSING",
        )

    @patch("payments.views.verify_transaction")
    def test_callback_rejects_wrong_reference(
        self,
        mock_verify,
    ):
        self.login()

        data = self.valid_transaction_data()
        data["reference"] = "WRONG-REFERENCE"

        mock_verify.return_value = data

        response = self.client.get(
            self.callback_url,
            {
                "reference":
                    self.payment.payment_reference
            },
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    @patch("payments.views.verify_transaction")
    def test_callback_rejects_wrong_currency(
        self,
        mock_verify,
    ):
        self.login()

        data = self.valid_transaction_data()
        data["currency"] = "USD"

        mock_verify.return_value = data

        response = self.client.get(
            self.callback_url,
            {
                "reference":
                    self.payment.payment_reference
            },
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.FAILED,
        )

    @patch("payments.views.verify_transaction")
    def test_callback_rejects_wrong_requested_amount(
        self,
        mock_verify,
    ):
        self.login()

        data = self.valid_transaction_data()
        data["requested_amount"] = 99999999

        mock_verify.return_value = data

        response = self.client.get(
            self.callback_url,
            {
                "reference":
                    self.payment.payment_reference
            },
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    @patch("payments.views.verify_transaction")
    def test_callback_rejects_missing_requested_amount(
        self,
        mock_verify,
    ):
        self.login()

        data = self.valid_transaction_data()
        data.pop("requested_amount")

        mock_verify.return_value = data

        response = self.client.get(
            self.callback_url,
            {
                "reference":
                    self.payment.payment_reference
            },
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    @patch("payments.views.verify_transaction")
    def test_callback_rejects_unsuccessful_transaction(
        self,
        mock_verify,
    ):
        self.login()

        data = self.valid_transaction_data()
        data["status"] = "failed"

        mock_verify.return_value = data

        response = self.client.get(
            self.callback_url,
            {
                "reference":
                    self.payment.payment_reference
            },
        )

        self.payment.refresh_from_db()

        self.order.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            self.order.payment_status,
            "FAILED",
        )

    def test_callback_rejects_other_users_payment(self):
        self.client.login(
            username="otheruser",
            password="TestPassword123!",
        )

        response = self.client.get(
            self.callback_url,
            {
                "reference":
                    self.payment.payment_reference
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("my_orders"),
        )

    def test_callback_already_successful(self):
        self.login()

        self.payment.status = (
            Payment.Status.SUCCESSFUL
        )
        self.payment.save()

        response = self.client.get(
            self.callback_url,
            {
                "reference":
                    self.payment.payment_reference
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            self.order.order_number,
            response.url,
        )