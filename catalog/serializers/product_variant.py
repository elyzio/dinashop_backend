from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from catalog.models import ProductVariant
from catalog.serializers.product_image import ProductImageSerializer


class ProductVariantSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    in_hand = serializers.SerializerMethodField()
    promised = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()
    last_landed_cost_cents = serializers.SerializerMethodField()
    active_price_cents = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product",
            "sku",
            "barcode",
            "is_active",
            "selling_price_cents",
            "sale_price_cents",
            "sale_starts_at",
            "sale_ends_at",
            "active_price_cents",
            "options",
            "in_hand",
            "promised",
            "available",
            "last_landed_cost_cents",
            "last_sale_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_options(self, obj) -> dict[str, str]:
        return {
            assignment.option.name: assignment.value.value
            for assignment in obj.option_assignments.all()
        }

    @staticmethod
    def _inventory(obj):
        return getattr(obj, "inventory", None)

    def get_in_hand(self, obj) -> int:
        inventory = self._inventory(obj)
        return inventory.in_hand if inventory else 0

    def get_promised(self, obj) -> int:
        inventory = self._inventory(obj)
        return inventory.promised if inventory else 0

    def get_available(self, obj) -> int:
        inventory = self._inventory(obj)
        return inventory.available if inventory else 0

    def get_last_landed_cost_cents(self, obj) -> int | None:
        inventory = self._inventory(obj)
        return inventory.last_landed_cost_cents if inventory else None


class ProductVariantPricingSerializer(serializers.Serializer):
    selling_price_cents = serializers.IntegerField(min_value=0, required=False)
    sale_price_cents = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    sale_starts_at = serializers.DateTimeField(allow_null=True, required=False)
    sale_ends_at = serializers.DateTimeField(allow_null=True, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one pricing field.")
        return attrs


class ProductVariantBarcodeGenerateSerializer(serializers.Serializer):
    pass


class ProductVariantBarcodeLookupSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(source="product.id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_brand = serializers.CharField(source="product.brand", read_only=True)
    primary_image = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    active_price_cents = serializers.IntegerField(read_only=True)
    is_sale_active = serializers.SerializerMethodField()
    available = serializers.SerializerMethodField()

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product_id",
            "product_name",
            "product_brand",
            "primary_image",
            "sku",
            "barcode",
            "options",
            "active_price_cents",
            "is_sale_active",
            "available",
        )
        read_only_fields = fields

    @extend_schema_field(ProductImageSerializer(allow_null=True))
    def get_primary_image(self, obj):
        image = next(iter(obj.product.images.all()), None)
        if image is None:
            return None
        return ProductImageSerializer(image, context=self.context).data

    def get_options(self, obj) -> dict[str, str]:
        return {
            assignment.option.name: assignment.value.value
            for assignment in obj.option_assignments.all()
        }

    def get_is_sale_active(self, obj) -> bool:
        return obj.active_price_cents != obj.selling_price_cents

    def get_available(self, obj) -> int:
        inventory = getattr(obj, "inventory", None)
        return inventory.available if inventory else 0
