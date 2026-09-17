from django.urls import path

from . import views


urlpatterns = [
    path(
        "<str:order_number>/initialize/",
        views.initialize_payment_view,
        name="initialize_payment",
    ),

    path(
        "callback/",
        views.payment_callback,
        name="payment_callback",
    ),
    path(
    "webhook/",
    views.paystack_webhook,
    name="paystack_webhook",
    ),
    path(
    "<str:order_number>/retry/",
    views.retry_payment,
    name="retry_payment",
    ),
]