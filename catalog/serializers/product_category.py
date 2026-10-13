from rest_framework import serializers

from catalog.models import ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ProductCategory
        fields = (
            "id",
            "product",
            "product_name",
            "category",
            "category_name",
            "is_primary",
            "sort_order",
        )
        read_only_fields = fields
