from decimal import Decimal

from django.test import TestCase

from .models import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductSpecification,
)


class ProductModelTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics"
        )

        self.brand = Brand.objects.create(
            name="Alphix",
            category=self.category
        )

        self.product = Product.objects.create(
            name="Test Laptop",
            brand=self.brand,
            description="A test product.",
            price=Decimal("450000.00"),
            is_in_stock=True,
            quantity=10,
        )


    def test_category_creation(self):
        self.assertEqual(
            self.category.name,
            "Electronics"
        )

        self.assertEqual(
            str(self.category),
            "Electronics"
        )


    def test_brand_creation(self):
        self.assertEqual(
            self.brand.name,
            "Alphix"
        )

        self.assertEqual(
            self.brand.category,
            self.category
        )

        self.assertEqual(
            str(self.brand),
            "Alphix"
        )


    def test_product_creation(self):
        self.assertEqual(
            self.product.name,
            "Test Laptop"
        )

        self.assertEqual(
            self.product.price,
            Decimal("450000.00")
        )

        self.assertEqual(
            self.product.quantity,
            10
        )

        self.assertTrue(
            self.product.is_in_stock
        )


    def test_product_relationship_with_brand(self):
        self.assertEqual(
            self.brand.products.count(),
            1
        )

        self.assertEqual(
            self.brand.products.first(),
            self.product
        )


    def test_product_image_relationship(self):
        image = ProductImage.objects.create(
            product=self.product,
            image_url="https://example.com/laptop.jpg",
        )

        self.assertEqual(
            self.product.images.count(),
            1
        )

        self.assertEqual(
            self.product.images.first(),
            image
        )


    def test_product_specification_relationship(self):
        specification = ProductSpecification.objects.create(
            product=self.product,
            key="RAM",
            value="16GB",
        )

        self.assertEqual(
            self.product.specifications.count(),
            1
        )

        self.assertEqual(
            self.product.specifications.first(),
            specification
        )