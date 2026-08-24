from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):

    class Meta:

        model = Order

        fields = [
            "shipping_address",
            "phone_number",
        ]

        widgets = {

            "shipping_address": forms.TextInput(
                attrs={
                    "placeholder": "Enter your delivery address"
                }
            ),

            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "Enter your phone number"
                }
            ),

        }

class OrderStatusForm(forms.ModelForm):

    class Meta:

        model = Order

        fields = [
            "status"
        ]