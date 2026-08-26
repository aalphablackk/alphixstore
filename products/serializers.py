from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model= Product
        fields = '__all__'

    def to_representation(self, instance):

        representation = super().to_representation(instance)

        representation["brand"] = {
            "id": instance.brand.id,
            "name": instance.brand.name,
        }

        representation["category"] = {
            "id": instance.brand.category.id,
            "name": instance.brand.category.name,
        }

        return representation