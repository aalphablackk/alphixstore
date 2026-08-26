from django.shortcuts import render, get_object_or_404
from .models import Product
# Create your views here.

def home(request):
    products = Product.objects.prefetch_related('images').select_related('brand').order_by('?')[:4]
    return render(
        request,
        'products/home.html',
        context={
            'products':products
        }
    )
def all_products(request):
    products = Product.objects.prefetch_related('images').select_related('brand').order_by('-created_at')
    return render(
        request,
        'products/all_products.html',
        context={
            'products':products

        }
    )


def product_detail(request, product_id):

    product = get_object_or_404(
        Product.objects
        .select_related("brand", 'brand__category')
        .prefetch_related(
            "images",
            "specifications"
        ),
        id=product_id
    )


    return render(
        request,
        "products/product_detail.html",
        {
            "product": product
        }
    )