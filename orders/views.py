from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.
from django.contrib.auth.decorators import login_required
from .forms import CheckoutForm,OrderStatusForm
from products.models import Product
from .models import Order, OrderItem
from django.db import transaction
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q



def is_staff_user(user):

    return user.is_staff

@user_passes_test(is_staff_user)
def dashboard_orders(request):

    orders = Order.objects.select_related(
        "user"
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "orders/dashboard_orders.html",
        {
            "orders": orders
        }
    )

@user_passes_test(is_staff_user)
def dashboard_order_detail(request, order_number):

    order = get_object_or_404(
        Order.objects.select_related(
            "user"
        ).prefetch_related(
            "items__product__images"
        ),
        order_number=order_number
    )


    if request.method == "POST":

        action = request.POST.get("action")


        # =================================
        # UPDATE ORDER STATUS
        # =================================

        if action == "update_status":

            form = OrderStatusForm(
                request.POST,
                instance=order
            )

            if form.is_valid():

                old_status = order.status

                new_status = form.cleaned_data["status"]


                # ---------------------------------
                # Cancel order
                # ---------------------------------

                if (
                    new_status == "CANCELLED"
                    and old_status != ["PENDING", "PROCESSING"]
                ):

                    with transaction.atomic():

                        for item in order.items.select_related(
                            "product"
                        ):

                            product = item.product

                            product.quantity += item.quantity

                            product.is_in_stock = True

                            product.save()


                        order.status = "CANCELLED"

                        order.save()


                # ---------------------------------
                # Prevent cancelling twice
                # ---------------------------------

                elif (
                    new_status == "CANCELLED"
                    and old_status == "CANCELLED"
                ):

                    pass


                else:

                    form.save()


                return redirect(
                    "dashboard_order_detail",
                    order_number=order.order_number
                )


        # =================================
        # OTHER ACTIONS
        # =================================

    else:

        form = OrderStatusForm(
            instance=order
        )


    return render(
        request,
        "orders/dashboard_order_detail.html",
        {
            "order": order,
            "form": form,
        }
    )



@user_passes_test(is_staff_user)
def dashboard_orders(request):

    orders = Order.objects.select_related(
        "user"
    ).order_by(
        "-created_at"
    )


    # ================================
    # SEARCH
    # ================================

    search = request.GET.get(
        "search",
        ""
    ).strip()


    if search:

        orders = orders.filter(

            Q(
                order_number__icontains=search
            )

            |

            Q(
                user__username__icontains=search
            )

        )


    # ================================
    # ORDER STATUS FILTER
    # ================================

    status = request.GET.get(
        "status",
        ""
    )


    if status:

        orders = orders.filter(
            status=status
        )


    # ================================
    # PAYMENT STATUS FILTER
    # ================================

    payment_status = request.GET.get(
        "payment_status",
        ""
    )


    if payment_status:

        orders = orders.filter(
            payment_status=payment_status
        )


    return render(

        request,

        "orders/dashboard_orders.html",

        {
            "orders": orders,

            "search": search,

            "selected_status": status,

            "selected_payment_status": payment_status,

            "status_choices": Order.STATUS_CHOICES,

            "payment_status_choices": Order.PAYMENT_STATUS_CHOICES,

        }

    )

@login_required(login_url="/accounts/login/")
def checkout(request):

    cart = request.session.get("cart", {})

    if not cart:
        return redirect("cart")

    # profile = request.user.userprofile

    cart_products = []

    total_amount = 0

    for product_id, quantity in cart.items():

        product = get_object_or_404(
            Product.objects.prefetch_related("images"),
            id=product_id
        )

        quantity = int(quantity)

        subtotal = product.price * quantity

        total_amount += subtotal

        cover_image = product.images.filter(
            is_cover=True
        ).first()

        cart_products.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
            "cover_image": cover_image,
        })


    if request.method == "POST":

        form = CheckoutForm(request.POST)

        if form.is_valid():

            # Stock validation
            for item in cart_products:

                product = item["product"]

                quantity = item["quantity"]

                if not product.is_in_stock:

                    form.add_error(
                        None,
                        f"{product.name} is currently out of stock."
                    )

                    return render(
                        request,
                        "orders/checkout.html",
                        {
                            "form": form,
                            "cart_products": cart_products,
                            "total_amount": total_amount,
                        }
                    )

                if quantity > product.quantity:

                    form.add_error(
                        None,
                        f"Only {product.quantity} unit(s) of "
                        f"{product.name} are available."
                    )

                    return render(
                        request,
                        "orders/checkout.html",
                        {
                            "form": form,
                            "cart_products": cart_products,
                            "total_amount": total_amount,
                        }
                    )


            with transaction.atomic():

                order = Order.objects.create(

                    user=request.user,

                    total_amount=total_amount,

                    shipping_address=form.cleaned_data[
                        "shipping_address"
                    ],

                    phone_number=form.cleaned_data[
                        "phone_number"
                    ],

                )


                for item in cart_products:

                    product = item["product"]

                    quantity = item["quantity"]


                    OrderItem.objects.create(

                        order=order,

                        product=product,

                        quantity=quantity,

                        price=product.price,

                        subtotal=item["subtotal"],

                    )


                    product.quantity -= quantity


                    if product.quantity <= 0:

                        product.quantity = 0

                        product.is_in_stock = False


                    product.save()


            request.session["cart"] = {}

            request.session.modified = True


            return redirect(
                "order_detail",
                order_number=order.order_number
            )


    else:


        form = CheckoutForm()


    return render(
        request,
        "orders/checkout.html",
        {
            "form": form,
            "cart_products": cart_products,
            "total_amount": total_amount,
        }
    )

@login_required(login_url="/accounts/login/")
def order_detail(request, order_number):

    order = get_object_or_404(
        Order,
        order_number=order_number,
        user=request.user
    )

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
        }
    )


@login_required(login_url="/accounts/login/")
def my_orders(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "orders/my_orders.html",
        {
            "orders": orders
        }
    )

