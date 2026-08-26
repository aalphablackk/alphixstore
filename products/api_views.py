from django.db import transaction

from rest_framework import permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework import viewsets

from .models import Product
from .serializers import ProductSerializer


class IsStaffOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):

        if request.method in permissions.SAFE_METHODS:
            return True

        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


class ProductViewset(viewsets.ModelViewSet):

    queryset = Product.objects.select_related(
        "brand",
        "brand__category"
    )

    serializer_class = ProductSerializer

    permission_classes = [
        IsStaffOrReadOnly
    ]

    def create(self, request, *args, **kwargs):

        data = request.data

        # Check whether we received multiple products
        many = isinstance(data, list)

        serializer = self.get_serializer(
            data=data,
            many=many
        )

        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    # X-CSRFToken: abc123456789
# Cookie: sessionid=xyz987654321; csrftoken=abc123456789