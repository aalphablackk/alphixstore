from django.shortcuts import render, redirect, get_object_or_404

from products.models import Product

# Create your views here.

def cart(request):
    cart = request.session.get('cart', {})

    cart_items=[]
    cart_total=0

    for product_id, quantity in cart.items():

        product = get_object_or_404(
            Product.objects.prefetch_related("images"),
            id=product_id
        )

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


    return render(
        request,
        "cart/cart.html",
        {
            "cart_items": cart_items,
            "cart_total": cart_total,
        }
    )

    

    return render(
        request,
        'cart/cart.html'
    )

def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart = request.session.get('cart', {})

    product_id = str(product.id)

    if product_id in cart:
        cart[product_id] +=1
    else:
        cart[product_id] = 1

    request.session['cart']= cart

    request.session.modified = True

    print(cart)

    return redirect(
        "cart"
    )

def update_cart(request, product_id):

    cart = request.session.get("cart", {})

    product_id = str(product_id)

    if product_id in cart:

        quantity = int(request.POST.get("quantity", 1))

        if quantity > 0:

            cart[product_id] = quantity

        else:

            del cart[product_id]

    request.session["cart"] = cart

    request.session.modified = True

    return redirect("cart")


def remove_from_cart(request, product_id):

    cart = request.session.get("cart", {})

    product_id = str(product_id)

    if product_id in cart:

        del cart[product_id]

    request.session["cart"] = cart

    request.session.modified = True

    return redirect("cart")


def clear_cart(request):

    request.session["cart"] = {}

    request.session.modified = True

    return redirect("cart")

        
