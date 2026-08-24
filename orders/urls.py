from django.urls import path
from . import views




urlpatterns = [

    path("checkout/",views.checkout,name="checkout"),
    path("my-orders/",views.my_orders,name="my_orders"),
    path("dashboard/",views.dashboard_orders,name="dashboard_orders"),
    path("dashboard/<str:order_number>/",views.dashboard_order_detail,name="dashboard_order_detail"),
    path("<str:order_number>/",views.order_detail,name="order_detail"),

]