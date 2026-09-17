from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_order_confirmation_email(order):
    """
    Send an email immediately after an order is successfully created.
    """

    if not order.user.email:
        return

    subject = f"Order Confirmation - {order.order_number}"

    context = {
        "order": order,
        "items": order.items.select_related("product").all(),
    }

    text_content = render_to_string(
        "emails/order_confirmation.txt",
        context,
    )

    html_content = render_to_string(
        "emails/order_confirmation.html",
        context,
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            None,
        ),
        to=[order.user.email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send(fail_silently=True)


def send_payment_confirmation_email(payment):
    """
    Send an email after a payment has been successfully confirmed.
    """

    order = payment.order

    if not order.user.email:
        return

    subject = f"Payment Confirmed - {order.order_number}"

    context = {
        "order": order,
        "payment": payment,
        "items": order.items.select_related("product").all(),
    }

    text_content = render_to_string(
        "emails/payment_confirmation.txt",
        context,
    )

    html_content = render_to_string(
        "emails/payment_confirmation.html",
        context,
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(
            settings,
            "DEFAULT_FROM_EMAIL",
            None,
        ),
        to=[order.user.email],
    )

    email.attach_alternative(
        html_content,
        "text/html",
    )

    email.send(fail_silently=True)