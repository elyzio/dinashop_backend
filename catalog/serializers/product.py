from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

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
    barcode = serializers.CharField(
        max_length=100,
        allow_blank=True,
        allow_null=True,
        required=False,
        trim_whitespace=True,
    )
    generate_barcode = serializers.BooleanField(required=False, default=False)
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

    def validate_barcode(self, value):
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if any(ord(character) < 32 or ord(character) > 126 for character in value):
            raise serializers.ValidationError(
                "Barcode may contain printable ASCII characters only."
            )
        return value

    def validate(self, attrs):
        if attrs.get("generate_barcode") and attrs.get("barcode"):
            raise serializers.ValidationError(
                {"barcode": "Enter a barcode or request generation, not both."}
            )
        return attrs


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


class ProductListSerializer(serializers.ModelSerializer):
    primary_category_id = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    display_price_cents = serializers.SerializerMethodField()
    available_quantity = serializers.SerializerMethodField()
    availability_status = serializers.SerializerMethodField()
    active_variant_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "brand",
            "visibility",
            "has_variants",
            "primary_category_id",
            "primary_image",
            "display_price_cents",
            "available_quantity",
            "availability_status",
            "active_variant_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    @extend_schema_field(serializers.UUIDField(allow_null=True))
    def get_primary_category_id(self, obj) -> str | None:
        link = next((item for item in obj.category_links.all() if item.is_primary), None)
        return str(link.category_id) if link else None

    @extend_schema_field(ProductImageSerializer(allow_null=True))
    def get_primary_image(self, obj) -> dict | None:
        image = next(iter(obj.images.all()), None)
        if not image:
            return None
        return ProductImageSerializer(image, context=self.context).data

    def _active_variants(self, obj):
        return [variant for variant in obj.variants.all() if variant.is_active]

    @extend_schema_field(serializers.IntegerField(min_value=0))
    def get_display_price_cents(self, obj) -> int:
        prices = [variant.active_price_cents for variant in self._active_variants(obj)]
        return min(prices) if prices else 0

    @extend_schema_field(serializers.IntegerField(min_value=0))
    def get_available_quantity(self, obj) -> int:
        return sum(
            max(0, variant.inventory.in_hand - variant.inventory.promised)
            for variant in self._active_variants(obj)
        )

    @extend_schema_field(serializers.ChoiceField(choices=("available", "low", "sold_out", "hidden")))
    def get_availability_status(self, obj) -> str:
        if obj.visibility == Product.Visibility.HIDDEN:
            return "hidden"
        quantity = self.get_available_quantity(obj)
        if quantity <= 0:
            return "sold_out"
        if quantity <= 5:
            return "low"
        return "available"

    @extend_schema_field(serializers.IntegerField(min_value=0))
    def get_active_variant_count(self, obj) -> int:
        return len(self._active_variants(obj))
