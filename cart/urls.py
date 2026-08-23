from django.urls import path
from . import views


urlpatterns = [
    path('',views.cart, name='cart'),
    path('add/<int:product_id>/',views.add_to_cart, name='add_to_cart'),
    path("update/<int:product_id>/",views.update_cart,name="update_cart"),
    path("remove/<int:product_id>/",views.remove_from_cart,name="remove_from_cart"),
    path("clear/",views.clear_cart,name="clear_cart"),

]