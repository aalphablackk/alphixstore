from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count
from orders.models import Order
from django.contrib.auth.models import User
from django.db.models.functions import TruncDate

# from accounts.decorators import role_required
# from django.contrib.auth.decorators import user_passes_test


def is_staff(user):
    return user.is_authenticated and user.is_staff


from products.models import (
    Product,
    Category,
    ProductImage,
    ProductSpecification
)

from products.forms import (
    ProductForm,
    CategoryForm,
    BrandForm,
    ProductImageForm,
    ProductSpecificationForm
)


# Dashboard Home
@login_required
@user_passes_test(is_staff, login_url="/")
@login_required
@user_passes_test(is_staff, login_url="/")
def dashboard_home(request):

    # ==========================================
    # BASIC STATISTICS
    # ==========================================

    total_products = Product.objects.count()

    total_categories = Category.objects.count()

    total_orders = Order.objects.count()

    total_customers = User.objects.filter(
        is_staff=False
    ).count()


    # ==========================================
    # ORDER STATISTICS
    # ==========================================

    pending_orders = Order.objects.filter(
        status="PENDING"
    ).count()

    processing_orders = Order.objects.filter(
        status="PROCESSING"
    ).count()

    shipped_orders = Order.objects.filter(
        status="SHIPPED"
    ).count()

    delivered_orders = Order.objects.filter(
        status="DELIVERED"
    ).count()

    cancelled_orders = Order.objects.filter(
        status="CANCELLED"
    ).count()


    # ==========================================
    # STOCK STATISTICS
    # ==========================================

    low_stock_products = Product.objects.filter(
        is_in_stock=True,
        quantity__lte=5,
        quantity__gt=0
    ).count()

    out_of_stock_products = Product.objects.filter(
        is_in_stock=False
    ).count()


    # ==========================================
    # TOTAL REVENUE
    # ==========================================

    revenue_result = Order.objects.filter(
        payment_status="PAID"
    ).aggregate(
        total=Sum("total_amount")
    )

    total_revenue = revenue_result["total"] or 0


    # ==========================================
    # RECENT ORDERS
    # ==========================================

    recent_orders = Order.objects.select_related(
        "user"
    ).order_by(
        "-created_at"
    )[:5]


    # ==========================================
    # REVENUE ANALYTICS
    # LAST 30 DAYS
    # ==========================================

    revenue_data = (
        Order.objects
        .filter(
            payment_status="PAID"
        )
        .annotate(
            day=TruncDate("created_at")
        )
        .values("day")
        .annotate(
            revenue=Sum("total_amount")
        )
        .order_by("day")
    )


    # ==========================================
    # ORDER ANALYTICS
    # LAST 30 DAYS
    # ==========================================

    order_data = (
        Order.objects
        .annotate(
            day=TruncDate("created_at")
        )
        .values("day")
        .annotate(
            orders=Count("id")
        )
        .order_by("day")
    )


    # ==========================================
    # PREPARE CHART DATA
    # ==========================================

    revenue_chart_labels = []

    revenue_chart_values = []

    for item in revenue_data:

        revenue_chart_labels.append(
            item["day"].strftime("%b %d")
        )

        revenue_chart_values.append(
            float(item["revenue"] or 0)
        )


    order_chart_labels = []

    order_chart_values = []

    for item in order_data:

        order_chart_labels.append(
            item["day"].strftime("%b %d")
        )

        order_chart_values.append(
            item["orders"] or 0
        )


    # ==========================================
    # CONTEXT
    # ==========================================

    context = {

        # Basic
        "total_products": total_products,
        "total_categories": total_categories,
        "total_orders": total_orders,
        "total_customers": total_customers,

        # Orders
        "pending_orders": pending_orders,
        "processing_orders": processing_orders,
        "shipped_orders": shipped_orders,
        "delivered_orders": delivered_orders,
        "cancelled_orders": cancelled_orders,

        # Stock
        "low_stock_products": low_stock_products,
        "out_of_stock_products": out_of_stock_products,

        # Revenue
        "total_revenue": total_revenue,

        # Recent orders
        "recent_orders": recent_orders,

        # Charts
        "revenue_chart_labels": revenue_chart_labels,
        "revenue_chart_values": revenue_chart_values,

        "order_chart_labels": order_chart_labels,
        "order_chart_values": order_chart_values,

    }


    return render(
        request,
        "dashboard/index.html",
        context
    )



# Product List

@login_required
@user_passes_test(is_staff, login_url="/")

def product_list(request):

    products = Product.objects.prefetch_related(
        'images',
        'specifications'
    ).select_related(
        'brand'
    ).order_by(
        '-created_at'
    )


    return render(
        request,
        'dashboard/product_list.html',
        {
            'products': products
        }
    )



# Add Product + Brand + Category

@login_required
@user_passes_test(is_staff, login_url="/")

def product_add(request):

    product_form = ProductForm()
    brand_form = BrandForm()
    category_form = CategoryForm()



    if request.method == "POST":


        form_type = request.POST.get("form_type")



        # PRODUCT FORM

        if form_type == "product":


            product_form = ProductForm(
                request.POST
            )


            if product_form.is_valid():


                product = product_form.save()



                return redirect(
                    "product_images",
                    product_id=product.id
                )




        # BRAND FORM

        elif form_type == "brand":


            brand_form = BrandForm(
                request.POST
            )


            if brand_form.is_valid():

                brand_form.save()


                return redirect(
                    "product_add"
                )




        # CATEGORY FORM

        elif form_type == "category":


            category_form = CategoryForm(
                request.POST
            )


            if category_form.is_valid():

                category_form.save()


                return redirect(
                    "product_add"
                )




    return render(
        request,
        "dashboard/product_add.html",
        {
            "product_form": product_form,
            "brand_form": brand_form,
            "category_form": category_form,
        }
    )





# Product Images


@login_required
@user_passes_test(is_staff, login_url="/")

def product_images(request, product_id):


    product = get_object_or_404(
        Product.objects.prefetch_related("images"),
        id=product_id
    )



    if request.method == "POST":


        form = ProductImageForm(
            request.POST,
            request.FILES
        )



        if form.is_valid():


            image = form.save(
                commit=False
            )


            image.product = product


            image.save()



            return redirect(
                "product_images",
                product_id=product.id
            )



    else:

        form = ProductImageForm()



    return render(
        request,
        "dashboard/product_images.html",
        {
            "form": form,
            "product": product,
            "images": product.images.all()
        }
    )





# Product Specifications


@login_required
@user_passes_test(is_staff, login_url="/")

def product_specifications(request, product_id):


    product = get_object_or_404(
        Product,
        id=product_id
    )



    if request.method == "POST":


        form = ProductSpecificationForm(
            request.POST
        )



        if form.is_valid():


            specification = form.save(
                commit=False
            )


            specification.product = product


            specification.save()



            return redirect(
                "product_specifications",
                product_id=product.id
            )



    else:

        form = ProductSpecificationForm()




    return render(
        request,
        "dashboard/product_specifications.html",
        {
            "form": form,
            "product": product,
            "specifications": product.specifications.all()
        }
    )





# Edit Product


@login_required
@user_passes_test(is_staff, login_url="/")

def product_edit(request, product_id):


    product = get_object_or_404(
        Product,
        id=product_id
    )



    if request.method == "POST":


        form = ProductForm(
            request.POST,
            instance=product
        )



        if form.is_valid():

            form.save()


            return redirect(
                "product_list"
            )



    else:


        form = ProductForm(
            instance=product
        )




    return render(
        request,
        "dashboard/product_edit.html",
        {
            "form": form,
            "product": product
        }
    )





# Delete Product


@login_required
@user_passes_test(is_staff, login_url="/")

def product_delete(request, product_id):


    if request.method == "POST":


        product = get_object_or_404(
            Product,
            id=product_id
        )


        product.delete()



    return redirect(
        "product_list"
    )





# Delete Product Image


@login_required
@user_passes_test(is_staff, login_url="/")

def delete_product_image(request, image_id):


    if request.method == "POST":


        image = get_object_or_404(
            ProductImage,
            id=image_id
        )


        product_id = image.product.id


        image.delete()



        return redirect(
            "product_images",
            product_id=product_id
        )



    return redirect(
        "product_list"
    )





# Set Cover Image


@login_required
@user_passes_test(is_staff, login_url="/")

def set_cover_image(request, image_id):


    if request.method == "POST":


        image = get_object_or_404(
            ProductImage,
            id=image_id
        )


        product = image.product



        # Remove existing cover

        ProductImage.objects.filter(
            product=product
        ).update(
            is_cover=False
        )



        # Set selected image as cover

        image.is_cover = True

        image.save()



        return redirect(
            "product_images",
            product_id=product.id
        )



    return redirect(
        "product_list"
    )





# Delete Specification


@login_required
@user_passes_test(is_staff, login_url="/")

def delete_specification(request, specification_id):


    if request.method == "POST":


        specification = get_object_or_404(
            ProductSpecification,
            id=specification_id
        )


        product_id = specification.product.id


        specification.delete()



        return redirect(
            "product_specifications",
            product_id=product_id
        )



    return redirect(
        "product_list"
    )





# Edit Specification


@login_required
@user_passes_test(is_staff, login_url="/")

def edit_specification(request, specification_id):

    specification = get_object_or_404(
        ProductSpecification,
        id=specification_id
    )


    if request.method == "POST":

        form = ProductSpecificationForm(
            request.POST,
            instance=specification
        )


        if form.is_valid():

            form.save()



    return redirect(
        "product_specifications",
        product_id=specification.product.id
    )
