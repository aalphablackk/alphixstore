from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.
from django.contrib.auth.decorators import login_required
from .forms import CheckoutForm,OrderStatusForm
from products.models import Product
from .models import Order, OrderItem
from django.db import transaction
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.contrib import messages
from .email_service import send_order_confirmation_email
from .services import cancel_order_and_restore_stock



def is_staff_user(user):

    return user.is_staff


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

                if new_status == "CANCELLED" and old_status != "CANCELLED":


                        cancel_order_and_restore_stock(order)


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

    cart_data = request.session.get("cart", {})

    if not cart_data:
        return redirect("cart")

    cart_products = []
    total_amount = 0

    # ---------------------------------
    # Get products and validate stock
    # ---------------------------------

    for product_id, quantity in cart_data.items():

        try:
            quantity = int(quantity)

        except (TypeError, ValueError):

            del cart_data[product_id]

            request.session["cart"] = cart_data
            request.session.modified = True

            messages.error(
                request,
                "An invalid item was found in your cart."
            )

            return redirect("cart")

        if quantity <= 0:

            del cart_data[product_id]

            request.session["cart"] = cart_data
            request.session.modified = True

            continue

        product = (
            Product.objects
            .prefetch_related("images")
            .filter(id=product_id)
            .first()
        )

        if not product:

            messages.error(
                request,
                "One of the products in your cart "
                "is no longer available."
            )

            return redirect("cart")

        # ---------------------------------
        # Stock validation
        # ---------------------------------

        if not product.is_in_stock or product.quantity <= 0:

            messages.error(
                request,
                f"{product.name} is currently out of stock."
            )

            return redirect("cart")

        if quantity > product.quantity:

            messages.error(
                request,
                f"Only {product.quantity} unit(s) of "
                f"{product.name} are available."
            )

            return redirect("cart")

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

    # ---------------------------------
    # Checkout form
    # ---------------------------------

    if request.method == "POST":

        form = CheckoutForm(request.POST)

        if form.is_valid():

            try:

                with transaction.atomic():

                    # ---------------------------------
                    # Lock products
                    # ---------------------------------

                    locked_products = {}

                    for item in cart_products:

                        product = (
                            Product.objects
                            .select_for_update()
                            .get(id=item["product"].id)
                        )

                        # Re-check stock after locking

                        if (
                            not product.is_in_stock
                            or product.quantity < item["quantity"]
                        ):

                            raise ValueError(
                                f"Only {product.quantity} unit(s) "
                                f"of {product.name} are available."
                            )

                        locked_products[
                            product.id
                        ] = product

                    # ---------------------------------
                    # Create Order
                    # ---------------------------------

                    order = Order.objects.create(

                        user=request.user,

                        total_amount=total_amount,

                        shipping_address=form.cleaned_data[
                            "shipping_address"
                        ],

                        phone_number=form.cleaned_data[
                            "phone_number"
                        ],
                        stock_reserved=True,

                    )

                    # ---------------------------------
                    # Create Order Items + Deduct Stock
                    # ---------------------------------

                    for item in cart_products:

                        product = locked_products[
                            item["product"].id
                        ]

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

                        product.save(
                            update_fields=[
                                "quantity",
                                "is_in_stock",
                                "updated_at",
                            ]
                        )

                # ---------------------------------
                # Order created successfully
                # ---------------------------------
                # Clear cart because the cart has now
                # been converted into an Order.
                request.session["cart"] = {}
                request.session.modified = True
                transaction.on_commit(
                    lambda: send_order_confirmation_email(order)
                )
                messages.success(
                    request,
                    "Your order has been created successfully."
                )

                return redirect(
                    "order_detail",
                    order_number=order.order_number
                )

            except ValueError as exc:

                messages.error(
                    request,
                    str(exc)
                )

                return redirect("cart")

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

