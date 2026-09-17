from django import forms
from .models import Product, Category, Brand, ProductImage, ProductSpecification


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = [
            "name"
        ]


class BrandForm(forms.ModelForm):

    class Meta:
        model = Brand
        fields = [
            "name",
            "category"
        ]


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            "name",
            "brand",
            "description",
            "price",
            "is_in_stock",
            "quantity",
        ]

class ProductImageForm(forms.ModelForm):

    class Meta:
        model = ProductImage

        fields = [
            "image",
            "image_url",
            "is_cover",
        ]

        widgets = {
            "image": forms.ClearableFileInput(
                attrs={
                    "accept": "image/*"
                }
            ),
            "image_url": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com/image.jpg"
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        image = cleaned_data.get("image")
        image_url = cleaned_data.get("image_url")

        if not image and not image_url:
            raise forms.ValidationError(
                "Please upload an image or provide an image URL."
            )

        if image and image_url:
            raise forms.ValidationError(
                "Please use either an uploaded image or an image URL, not both."
            )

        return cleaned_data

class ProductSpecificationForm(forms.ModelForm):

    class Meta:

        model = ProductSpecification

        fields = [
            "key",
            "value",
        ]