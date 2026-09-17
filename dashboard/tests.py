from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from orders.models import Order
from products.models import Category, Brand, Product


class DashboardAccessTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="TestPassword123!",
        )

        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="TestPassword123!",
            is_staff=True,
        )

        self.dashboard_url = reverse("dashboard_home")

    def test_dashboard_requires_login(self):
        response = self.client.get(
            self.dashboard_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            "/accounts/login/",
            response.url,
        )

    def test_customer_cannot_access_dashboard(self):
        self.client.login(
            username="customer",
            password="TestPassword123!",
        )

        response = self.client.get(
            self.dashboard_url
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            "/?next=/dashboard/",
        )

    def test_staff_can_access_dashboard(self):
        self.client.login(
            username="staff",
            password="TestPassword123!",
        )

        response = self.client.get(
            self.dashboard_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/index.html",
        )


class DashboardStatisticsTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="dashboardstaff",
            email="dashboard@example.com",
            password="TestPassword123!",
            is_staff=True,
        )

        self.customer = User.objects.create_user(
            username="dashboardcustomer",
            email="customer@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Dashboard Category",
        )

        self.brand = Brand.objects.create(
            name="Dashboard Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Dashboard Product",
            brand=self.brand,
            description="Dashboard test product.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

        self.client.login(
            username="dashboardstaff",
            password="TestPassword123!",
        )

    def create_order(
        self,
        status="PENDING",
        payment_status="PENDING",
        total=Decimal("50000.00"),
    ):
        return Order.objects.create(
            user=self.customer,
            total_amount=total,
            status=status,
            payment_status=payment_status,
            shipping_address="Lagos, Nigeria",
            phone_number="08012345678",
            stock_reserved=True,
        )

    def test_dashboard_total_products(self):
        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["total_products"],
            1,
        )

    def test_dashboard_total_categories(self):
        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["total_categories"],
            1,
        )

    def test_dashboard_total_orders(self):
        self.create_order()

        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["total_orders"],
            1,
        )

    def test_dashboard_total_customers(self):
        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["total_customers"],
            1,
        )

    def test_dashboard_order_statistics(self):
        self.create_order(
            status="PENDING"
        )

        self.create_order(
            status="PROCESSING"
        )

        self.create_order(
            status="SHIPPED"
        )

        self.create_order(
            status="DELIVERED"
        )

        self.create_order(
            status="CANCELLED"
        )

        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["pending_orders"],
            1,
        )

        self.assertEqual(
            response.context["processing_orders"],
            1,
        )

        self.assertEqual(
            response.context["shipped_orders"],
            1,
        )

        self.assertEqual(
            response.context["delivered_orders"],
            1,
        )

        self.assertEqual(
            response.context["cancelled_orders"],
            1,
        )

    def test_dashboard_revenue_only_counts_paid_orders(self):
        self.create_order(
            payment_status="PAID",
            total=Decimal("100000.00"),
        )

        self.create_order(
            payment_status="PENDING",
            total=Decimal("50000.00"),
        )

        self.create_order(
            payment_status="FAILED",
            total=Decimal("25000.00"),
        )

        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["total_revenue"],
            Decimal("100000.00"),
        )

    def test_dashboard_low_stock_count(self):
        Product.objects.create(
            name="Low Stock Product",
            brand=self.brand,
            description="Low stock product.",
            price=Decimal("20000.00"),
            is_in_stock=True,
            quantity=3,
        )

        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["low_stock_products"],
            1,
        )

    def test_dashboard_out_of_stock_count(self):
        Product.objects.create(
            name="Out Of Stock Product",
            brand=self.brand,
            description="Out of stock product.",
            price=Decimal("20000.00"),
            is_in_stock=False,
            quantity=0,
        )

        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertEqual(
            response.context["out_of_stock_products"],
            1,
        )

    def test_dashboard_recent_orders(self):
        self.create_order()

        response = self.client.get(
            reverse("dashboard_home")
        )

        recent_orders = response.context[
            "recent_orders"
        ]

        self.assertEqual(
            len(recent_orders),
            1,
        )

    def test_dashboard_chart_context_exists(self):
        response = self.client.get(
            reverse("dashboard_home")
        )

        self.assertIn(
            "revenue_chart_labels",
            response.context,
        )

        self.assertIn(
            "revenue_chart_values",
            response.context,
        )

        self.assertIn(
            "order_chart_labels",
            response.context,
        )

        self.assertIn(
            "order_chart_values",
            response.context,
        )

# =========================================================
# PRODUCT MANAGEMENT
# =========================================================


class DashboardProductManagementTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="productstaff",
            email="productstaff@example.com",
            password="TestPassword123!",
            is_staff=True,
        )

        self.customer = User.objects.create_user(
            username="productcustomer",
            email="productcustomer@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Existing Category",
        )

        self.brand = Brand.objects.create(
            name="Existing Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Existing Product",
            brand=self.brand,
            description="Existing product description.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

        self.client.login(
            username="productstaff",
            password="TestPassword123!",
        )

    # =====================================================
    # PRODUCT LIST
    # =====================================================

    def test_staff_can_view_product_list(self):
        response = self.client.get(
            reverse("product_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/product_list.html",
        )

        self.assertIn(
            self.product,
            response.context["products"],
        )

    def test_customer_cannot_view_product_list(self):
        self.client.logout()

        self.client.login(
            username="productcustomer",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("product_list")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            "/?next=/dashboard/product_list/",
        )

    def test_product_list_requires_login(self):
        self.client.logout()

        response = self.client.get(
            reverse("product_list")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertIn(
            "/accounts/login/",
            response.url,
        )

    # =====================================================
    # PRODUCT ADD PAGE
    # =====================================================

    def test_staff_can_view_product_add_page(self):
        response = self.client.get(
            reverse("product_add")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/product_add.html",
        )

        self.assertIn(
            "product_form",
            response.context,
        )

        self.assertIn(
            "brand_form",
            response.context,
        )

        self.assertIn(
            "category_form",
            response.context,
        )

    def test_customer_cannot_view_product_add_page(self):
        self.client.logout()

        self.client.login(
            username="productcustomer",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse("product_add")
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            "/?next=/dashboard/product/add/",
        )

    # =====================================================
    # ADD CATEGORY
    # =====================================================

    def test_staff_can_add_category(self):
        response = self.client.post(
            reverse("product_add"),
            {
                "form_type": "category",
                "name": "New Category",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            Category.objects.filter(
                name="New Category"
            ).exists()
        )

        self.assertEqual(
            response.url,
            reverse("product_add"),
        )

    # =====================================================
    # ADD BRAND
    # =====================================================

    def test_staff_can_add_brand(self):
        response = self.client.post(
            reverse("product_add"),
            {
                "form_type": "brand",
                "name": "New Brand",
                "category": self.category.id,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            Brand.objects.filter(
                name="New Brand",
                category=self.category,
            ).exists()
        )

        self.assertEqual(
            response.url,
            reverse("product_add"),
        )

    # =====================================================
    # ADD PRODUCT
    # =====================================================

    def test_staff_can_add_product(self):
        response = self.client.post(
            reverse("product_add"),
            {
                "form_type": "product",
                "name": "New Product",
                "brand": self.brand.id,
                "description": "New product description.",
                "price": "75000.00",
                "is_in_stock": True,
                "quantity": 20,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        product = Product.objects.get(
            name="New Product"
        )

        self.assertEqual(
            product.brand,
            self.brand,
        )

        self.assertEqual(
            product.price,
            Decimal("75000.00"),
        )

        self.assertEqual(
            product.quantity,
            20,
        )

        self.assertEqual(
            response.url,
            reverse(
                "product_images",
                kwargs={
                    "product_id": product.id
                },
            ),
        )

    # =====================================================
    # EDIT PRODUCT
    # =====================================================

    def test_staff_can_edit_product(self):
        response = self.client.post(
            reverse(
                "product_edit",
                kwargs={
                    "product_id": self.product.id
                },
            ),
            {
                "name": "Updated Product",
                "brand": self.brand.id,
                "description": "Updated description.",
                "price": "85000.00",
                "is_in_stock": True,
                "quantity": 25,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.name,
            "Updated Product",
        )

        self.assertEqual(
            self.product.description,
            "Updated description.",
        )

        self.assertEqual(
            self.product.price,
            Decimal("85000.00"),
        )

        self.assertEqual(
            self.product.quantity,
            25,
        )

        self.assertEqual(
            response.url,
            reverse("product_list"),
        )

    def test_customer_cannot_edit_product(self):
        self.client.logout()

        self.client.login(
            username="productcustomer",
            password="TestPassword123!",
        )

        response = self.client.post(
            reverse(
                "product_edit",
                kwargs={
                    "product_id": self.product.id
                },
            ),
            {
                "name": "Unauthorized Update",
                "brand": self.brand.id,
                "description": "Unauthorized.",
                "price": "1.00",
                "is_in_stock": True,
                "quantity": 1,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.product.refresh_from_db()

        self.assertEqual(
            self.product.name,
            "Existing Product",
        )

    # =====================================================
    # DELETE PRODUCT
    # =====================================================

    def test_staff_can_delete_product(self):
        product_id = self.product.id

        response = self.client.post(
            reverse(
                "product_delete",
                kwargs={
                    "product_id": product_id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertEqual(
            response.url,
            reverse("product_list"),
        )

        self.assertFalse(
            Product.objects.filter(
                id=product_id
            ).exists()
        )

    def test_delete_product_requires_post(self):
        response = self.client.get(
            reverse(
                "product_delete",
                kwargs={
                    "product_id": self.product.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            Product.objects.filter(
                id=self.product.id
            ).exists()
        )

    def test_customer_cannot_delete_product(self):
        self.client.logout()

        self.client.login(
            username="productcustomer",
            password="TestPassword123!",
        )

        response = self.client.post(
            reverse(
                "product_delete",
                kwargs={
                    "product_id": self.product.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            Product.objects.filter(
                id=self.product.id
            ).exists()
        )
# =========================================================
# PRODUCT IMAGES & SPECIFICATIONS
# =========================================================

from products.models import (
    ProductImage,
    ProductSpecification,
)


class DashboardProductMediaTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="media_staff",
            email="media@example.com",
            password="TestPassword123!",
            is_staff=True,
        )

        self.customer = User.objects.create_user(
            username="media_customer",
            email="customer@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Media Category",
        )

        self.brand = Brand.objects.create(
            name="Media Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Media Product",
            brand=self.brand,
            description="Media test product.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

        self.client.login(
            username="media_staff",
            password="TestPassword123!",
        )

    # =====================================================
    # PRODUCT IMAGES PAGE
    # =====================================================

    def test_staff_can_view_product_images(self):
        response = self.client.get(
            reverse(
                "product_images",
                kwargs={
                    "product_id": self.product.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/product_images.html",
        )

        self.assertEqual(
            response.context["product"],
            self.product,
        )

    def test_customer_cannot_view_product_images(self):
        self.client.logout()

        self.client.login(
            username="media_customer",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "product_images",
                kwargs={
                    "product_id": self.product.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    # =====================================================
    # ADD PRODUCT IMAGE
    # =====================================================

    def test_staff_can_add_product_image_url(self):
        response = self.client.post(
            reverse(
                "product_images",
                kwargs={
                    "product_id": self.product.id
                },
            ),
            {
                "image_url": (
                    "https://example.com/product.jpg"
                ),
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            ProductImage.objects.filter(
                product=self.product,
                image_url="https://example.com/product.jpg",
            ).exists()
        )

    # =====================================================
    # SET COVER IMAGE
    # =====================================================

    def test_staff_can_set_cover_image(self):
        first_image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/first.jpg",
            is_cover=True,
        )

        second_image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/second.jpg",
            is_cover=False,
        )

        response = self.client.post(
            reverse(
                "set_cover_image",
                kwargs={
                    "image_id": second_image.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        first_image.refresh_from_db()
        second_image.refresh_from_db()

        self.assertFalse(
            first_image.is_cover,
        )

        self.assertTrue(
            second_image.is_cover,
        )

    def test_setting_cover_image_removes_existing_cover(self):
        first_image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/first.jpg",
            is_cover=True,
        )

        second_image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/second.jpg",
            is_cover=False,
        )

        self.client.post(
            reverse(
                "set_cover_image",
                kwargs={
                    "image_id": second_image.id
                },
            )
        )

        self.assertEqual(
            ProductImage.objects.filter(
                product=self.product,
                is_cover=True,
            ).count(),
            1,
        )

    # =====================================================
    # DELETE IMAGE
    # =====================================================

    def test_staff_can_delete_product_image(self):
        image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/delete.jpg",
        )

        image_id = image.id

        response = self.client.post(
            reverse(
                "delete_product_image",
                kwargs={
                    "image_id": image_id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            ProductImage.objects.filter(
                id=image_id
            ).exists()
        )

    def test_delete_product_image_requires_post(self):
        image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/delete.jpg",
        )

        response = self.client.get(
            reverse(
                "delete_product_image",
                kwargs={
                    "image_id": image.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            ProductImage.objects.filter(
                id=image.id
            ).exists()
        )

    def test_customer_cannot_delete_product_image(self):
        image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/delete.jpg",
        )

        self.client.logout()

        self.client.login(
            username="media_customer",
            password="TestPassword123!",
        )

        response = self.client.post(
            reverse(
                "delete_product_image",
                kwargs={
                    "image_id": image.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            ProductImage.objects.filter(
                id=image.id
            ).exists()
        )


class DashboardSpecificationTests(TestCase):

    def setUp(self):
        self.staff = User.objects.create_user(
            username="spec_staff",
            email="spec@example.com",
            password="TestPassword123!",
            is_staff=True,
        )

        self.customer = User.objects.create_user(
            username="spec_customer",
            email="speccustomer@example.com",
            password="TestPassword123!",
        )

        self.category = Category.objects.create(
            name="Specification Category",
        )

        self.brand = Brand.objects.create(
            name="Specification Brand",
            category=self.category,
        )

        self.product = Product.objects.create(
            name="Specification Product",
            brand=self.brand,
            description="Specification test product.",
            price=Decimal("50000.00"),
            is_in_stock=True,
            quantity=10,
        )

        self.client.login(
            username="spec_staff",
            password="TestPassword123!",
        )

    # =====================================================
    # SPECIFICATION PAGE
    # =====================================================

    def test_staff_can_view_specifications(self):
        response = self.client.get(
            reverse(
                "product_specifications",
                kwargs={
                    "product_id": self.product.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertTemplateUsed(
            response,
            "dashboard/product_specifications.html",
        )

        self.assertEqual(
            response.context["product"],
            self.product,
        )

    def test_customer_cannot_view_specifications(self):
        self.client.logout()

        self.client.login(
            username="spec_customer",
            password="TestPassword123!",
        )

        response = self.client.get(
            reverse(
                "product_specifications",
                kwargs={
                    "product_id": self.product.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    # =====================================================
    # ADD SPECIFICATION
    # =====================================================

    def test_staff_can_add_specification(self):
        response = self.client.post(
            reverse(
                "product_specifications",
                kwargs={
                    "product_id": self.product.id
                },
            ),
            {
                "key": "RAM",
                "value": "8GB",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            ProductSpecification.objects.filter(
                product=self.product,
                key="RAM",
                value="8GB",
            ).exists()
        )

    # =====================================================
    # EDIT SPECIFICATION
    # =====================================================

    def test_staff_can_edit_specification(self):
        specification = ProductSpecification.objects.create(
            product=self.product,
            key="RAM",
            value="8GB",
        )

        response = self.client.post(
            reverse(
                "edit_specification",
                kwargs={
                    "specification_id": specification.id
                },
            ),
            {
                "key": "RAM",
                "value": "16GB",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        specification.refresh_from_db()

        self.assertEqual(
            specification.key,
            "RAM",
        )

        self.assertEqual(
            specification.value,
            "16GB",
        )

    # =====================================================
    # DELETE SPECIFICATION
    # =====================================================

    def test_staff_can_delete_specification(self):
        specification = ProductSpecification.objects.create(
            product=self.product,
            key="Storage",
            value="256GB",
        )

        specification_id = specification.id

        response = self.client.post(
            reverse(
                "delete_specification",
                kwargs={
                    "specification_id": specification_id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertFalse(
            ProductSpecification.objects.filter(
                id=specification_id
            ).exists()
        )

    def test_delete_specification_requires_post(self):
        specification = ProductSpecification.objects.create(
            product=self.product,
            key="Storage",
            value="256GB",
        )

        response = self.client.get(
            reverse(
                "delete_specification",
                kwargs={
                    "specification_id": specification.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            ProductSpecification.objects.filter(
                id=specification.id
            ).exists()
        )

    def test_customer_cannot_delete_specification(self):
        specification = ProductSpecification.objects.create(
            product=self.product,
            key="Storage",
            value="256GB",
        )

        self.client.logout()

        self.client.login(
            username="spec_customer",
            password="TestPassword123!",
        )

        response = self.client.post(
            reverse(
                "delete_specification",
                kwargs={
                    "specification_id": specification.id
                },
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            ProductSpecification.objects.filter(
                id=specification.id
            ).exists()
        )