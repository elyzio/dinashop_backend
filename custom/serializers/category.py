from rest_framework import serializers

from custom.models import Category


class CategoryReadSerializer(serializers.ModelSerializer):
    parent_id = serializers.UUIDField(read_only=True, allow_null=True)
    child_count = serializers.IntegerField(read_only=True, default=0)
    product_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Category
        fields = (
            "id",
            "name",
            "slug",
            "parent_id",
            "status",
            "sort_order",
            "child_count",
            "product_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CategoryWriteSerializer(serializers.ModelSerializer):
    parent_id = serializers.PrimaryKeyRelatedField(
        source="parent",
        queryset=Category.objects.all(),
        allow_null=True,
        required=False,
    )

    class Meta:
        model = Category
        fields = ("name", "parent_id", "status", "sort_order")
        # Model validation in the category service handles sibling uniqueness
        # (including case-insensitive comparison) without making a nullable
        # parent mandatory in DRF's generated UniqueTogetherValidator.
        validators = []

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Category name cannot be empty.")
        return value
