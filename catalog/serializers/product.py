from rest_framework import serializers

from catalog.models import Product
from catalog.serializers.product_image import ProductImageSerializer
from catalog.serializers.product_option import ProductOptionSerializer
from catalog.serializers.product_variant import ProductVariantSerializer


class OptionDefinitionInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    values = serializers.ListField(
        child=serializers.CharField(max_length=100),
        allow_empty=False,
    )


class VariantInputSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False)
    sku = serializers.CharField(max_length=80)
    options = serializers.DictField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=dict,
    )
    selling_price_cents = serializers.IntegerField(min_value=0)
    sale_price_cents = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    sale_starts_at = serializers.DateTimeField(allow_null=True, required=False)
    sale_ends_at = serializers.DateTimeField(allow_null=True, required=False)
    is_active = serializers.BooleanField(required=False, default=True)


class ProductCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    description = serializers.CharField(allow_blank=True, required=False)
    brand = serializers.CharField(max_length=120, allow_blank=True, required=False)
    visibility = serializers.ChoiceField(
        choices=Product.Visibility.choices,
        required=False,
        default=Product.Visibility.ACTIVE,
    )
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )
    primary_category_id = serializers.UUIDField()
    option_definitions = OptionDefinitionInputSerializer(many=True, required=False, default=list)
    variants = VariantInputSerializer(many=True, allow_empty=False)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Product name cannot be empty.")
        return value

    def validate_category_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Category IDs must be unique.")
        return value

    def validate(self, attrs):
        if attrs["primary_category_id"] not in attrs["category_ids"]:
            raise serializers.ValidationError(
                {"primary_category_id": "The primary category must be selected."}
            )
        return attrs


class ProductUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    brand = serializers.CharField(max_length=120, allow_blank=True, required=False)
    category_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        required=False,
    )
    primary_category_id = serializers.UUIDField(required=False)

    def validate(self, attrs):
        category_ids = attrs.get("category_ids")
        primary_id = attrs.get("primary_category_id")
        if primary_id and category_ids is not None and primary_id not in category_ids:
            raise serializers.ValidationError(
                {"primary_category_id": "The primary category must be selected."}
            )
        return attrs


class ProductVariantGridSerializer(serializers.Serializer):
    option_definitions = OptionDefinitionInputSerializer(many=True, required=False, default=list)
    variants = VariantInputSerializer(many=True, allow_empty=False)


class ProductVisibilitySerializer(serializers.Serializer):
    visibility = serializers.ChoiceField(choices=Product.Visibility.choices)


class ProductReadSerializer(serializers.ModelSerializer):
    category_ids = serializers.SerializerMethodField()
    primary_category_id = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    option_definitions = ProductOptionSerializer(source="options", many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "description",
            "brand",
            "visibility",
            "has_variants",
            "category_ids",
            "primary_category_id",
            "images",
            "option_definitions",
            "variants",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_category_ids(self, obj) -> list[str]:
        return [str(link.category_id) for link in obj.category_links.all()]

    def get_primary_category_id(self, obj) -> str | None:
        link = next((item for item in obj.category_links.all() if item.is_primary), None)
        return str(link.category_id) if link else None
