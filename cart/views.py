from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from products.models import Product


def cart(request):
    cart_data = request.session.get("cart", {})

    cart_items = []
    cart_total = 0
    updated = False

    for product_id, quantity in list(cart_data.items()):

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            del cart_data[product_id]
            updated = True
            continue

        if quantity <= 0:
            del cart_data[product_id]
            updated = True
            continue

        product = Product.objects.prefetch_related("images").filter(
            id=product_id
        ).first()

        # Remove deleted products from the session cart
        if not product:
            del cart_data[product_id]
            updated = True
            continue

        # Keep cart quantity within available stock
        if quantity > product.quantity:
            quantity = product.quantity
            cart_data[product_id] = quantity
            updated = True

        # Remove product if it is no longer available
        if quantity <= 0 or not product.is_in_stock:
            del cart_data[product_id]
            updated = True
            continue

        cover_image = product.images.filter(
            is_cover=True
        ).first()

        subtotal = product.price * quantity

        cart_total += subtotal

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
            "cover_image": cover_image,
        })

    if updated:
        request.session["cart"] = cart_data
        request.session.modified = True

    return render(
        request,
        "cart/cart.html",
        {
            "cart_items": cart_items,
            "cart_total": cart_total,
        }
    )


def add_to_cart(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id
    )

    if not product.is_in_stock or product.quantity <= 0:

        messages.error(
            request,
            f"{product.name} is currently out of stock."
        )

        return redirect("cart")

    cart_data = request.session.get("cart", {})

    product_id = str(product.id)

    current_quantity = cart_data.get(product_id, 0)

    if current_quantity >= product.quantity:

        messages.warning(
            request,
            f"You cannot add more than {product.quantity} "
            f"unit(s) of {product.name}."
        )

        return redirect("cart")

    cart_data[product_id] = current_quantity + 1

    request.session["cart"] = cart_data
    request.session.modified = True

    messages.success(
        request,
        f"{product.name} added to your cart."
    )

    return redirect("cart")


def update_cart(request, product_id):

    if request.method != "POST":
        return redirect("cart")

    cart_data = request.session.get("cart", {})

    product_id = str(product_id)

    if product_id not in cart_data:
        return redirect("cart")

    product = Product.objects.filter(
        id=product_id
    ).first()

    if not product:
        del cart_data[product_id]

        request.session["cart"] = cart_data
        request.session.modified = True

        messages.error(
            request,
            "This product is no longer available."
        )

        return redirect("cart")

    try:
        quantity = int(
            request.POST.get("quantity", 1)
        )

    except (TypeError, ValueError):

        messages.error(
            request,
            "Please enter a valid quantity."
        )

        return redirect("cart")

    if quantity <= 0:

        del cart_data[product_id]

        messages.success(
            request,
            f"{product.name} removed from your cart."
        )

    elif not product.is_in_stock or product.quantity <= 0:

        del cart_data[product_id]

        messages.error(
            request,
            f"{product.name} is currently out of stock."
        )

    elif quantity > product.quantity:

        cart_data[product_id] = product.quantity

        messages.warning(
            request,
            f"Only {product.quantity} unit(s) of "
            f"{product.name} are available."
        )

    else:

        cart_data[product_id] = quantity

    request.session["cart"] = cart_data
    request.session.modified = True

    return redirect("cart")


def remove_from_cart(request, product_id):

    if request.method != "POST":
        return redirect("cart")

    cart_data = request.session.get("cart", {})

    product_id = str(product_id)

    if product_id in cart_data:

        del cart_data[product_id]

    request.session["cart"] = cart_data
    request.session.modified = True

    return redirect("cart")


def clear_cart(request):

    if request.method != "POST":
        return redirect("cart")

    request.session["cart"] = {}
    request.session.modified = True

    messages.success(
        request,
        "Your cart has been cleared."
    )

    return redirect("cart")