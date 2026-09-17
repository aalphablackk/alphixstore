from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category, Brand
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
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

    products = Product.objects.prefetch_related(
        "images"
    ).select_related(
        "brand",
        "brand__category"
    )

    # =================================
    # SEARCH
    # =================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        products = products.filter(

            Q(name__icontains=search)

            |

            Q(description__icontains=search)

            |

            Q(brand__name__icontains=search)

        )

    # =================================
    # CATEGORY FILTER
    # =================================

    category = request.GET.get(
        "category",
        ""
    ).strip()

    if category:

        products = products.filter(
            brand__category__id=category
        )

    # =================================
    # BRAND FILTER
    # =================================

    brand = request.GET.get(
        "brand",
        ""
    ).strip()

    if brand:

        products = products.filter(
            brand__id=brand
        )

    # =================================
    # MINIMUM PRICE
    # =================================

    min_price = request.GET.get(
        "min_price",
        ""
    ).strip()

    if min_price:

        try:
            min_price = Decimal(min_price)

            if min_price >= 0:
                products = products.filter(
                    price__gte=min_price
                )
            else:
                min_price = ""

        except (InvalidOperation, ValueError, TypeError):
            min_price = ""

    # =================================
    # MAXIMUM PRICE
    # =================================

    max_price = request.GET.get(
        "max_price",
        ""
    ).strip()

    if max_price:

        try:
            max_price = Decimal(max_price)

            if max_price >= 0:
                products = products.filter(
                    price__lte=max_price
                )
            else:
                max_price = ""

        except (InvalidOperation, ValueError, TypeError):
            max_price = ""

    # =================================
    # AVAILABILITY
    # =================================

    availability = request.GET.get(
        "availability",
        ""
    ).strip()

    if availability == "in_stock":

        products = products.filter(
            is_in_stock=True,
            quantity__gt=0
        )

    elif availability == "out_of_stock":

        products = products.filter(
            Q(is_in_stock=False)
            |
            Q(quantity=0)
        )

    # =================================
    # SORTING
    # =================================

    sort = request.GET.get(
        "sort",
        "newest"
    )

    sort_options = {

        "newest": "-created_at",

        "oldest": "created_at",

        "price_low": "price",

        "price_high": "-price",

        "name_az": "name",

        "name_za": "-name",

    }

    products = products.order_by(
        sort_options.get(
            sort,
            "-created_at"
        )
    )
    total_products = products.count()

    # Pagination
    paginator = Paginator(products, 12)

    page_number = request.GET.get("page")
    products_page = paginator.get_page(page_number)

    # =================================
    # FILTER OPTIONS
    # =================================

    categories = Category.objects.order_by(
        "name"
    )

    brands = Brand.objects.select_related(
        "category"
    ).order_by(
        "name"
    )

    return render(
        request,
        "products/all_products.html",
        {
            "products": products_page,

            "total_products": total_products,

            "categories": categories,

            "brands": brands,

            "search": search,

            "selected_category": category,

            "selected_brand": brand,

            "min_price": min_price,

            "max_price": max_price,

            "selected_availability": availability,

            "selected_sort": sort,
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