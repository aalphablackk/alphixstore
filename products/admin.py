from django.contrib import admin

from .models import (
    Category,
    Brand,
    Product,
    ProductImage,
    ProductSpecification,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "-created_at",
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "category",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "name",
        "category__name",
    )

    list_filter = (
        "category",
        "created_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "brand",
        "price",
        "quantity",
        "stock_status",
        "created_at",
        "updated_at",
    )

    search_fields = (
        "name",
        "description",
        "brand__name",
    )

    list_filter = (
        "is_in_stock",
        "brand",
        "created_at",
    )

    list_editable = (
        "quantity",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )

    @admin.display(
        boolean=True,
        description="In Stock",
    )
    def stock_status(self, obj):
        return obj.quantity > 0
    

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "is_cover",
        "created_at",
    )

    search_fields = (
        "product__name",
    )

    list_filter = (
        "is_cover",
        "created_at",
    )

    ordering = (
        "-created_at",
    )


@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "key",
        "value",
        "created_at",
    )

    search_fields = (
        "product__name",
        "key",
        "value",
    )

    list_filter = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )