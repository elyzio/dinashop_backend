from urllib.parse import quote

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from custom.whatsapp import whatsapp_digits


def _public_variants(product):
    return getattr(product, "public_variants", ())


def _available(variant) -> bool:
    inventory = getattr(variant, "inventory", None)
    return bool(inventory and inventory.available > 0)


class PublicRenditionSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("thumbnail", "card", "detail"))
    image_url = serializers.URLField(allow_null=True)
    width = serializers.IntegerField(min_value=1)
    height = serializers.IntegerField(min_value=1)
    file_size_bytes = serializers.IntegerField(min_value=0)


class PublicProductImageSerializer(serializers.Serializer):
    image_url = serializers.URLField(allow_null=True)
    alt_text = serializers.CharField(allow_blank=True)
    sort_order = serializers.IntegerField(min_value=0)
    width = serializers.IntegerField(min_value=1, allow_null=True)
    height = serializers.IntegerField(min_value=1, allow_null=True)
    renditions = PublicRenditionSerializer(many=True)

    def to_representation(self, image):
        request = self.context.get("request")

        def absolute(file):
            if not file:
                return None
            url = file.url
            return request.build_absolute_uri(url) if request else url

        return {
            "image_url": absolute(image.image),
            "alt_text": image.alt_text,
            "sort_order": image.sort_order,
            "width": image.width,
            "height": image.height,
            "renditions": [
                {
                    "kind": rendition.kind,
                    "image_url": absolute(rendition.image),
                    "width": rendition.width,
                    "height": rendition.height,
                    "file_size_bytes": rendition.file_size_bytes,
                }
                for rendition in image.renditions.all()
            ],
        }


class PublicCategorySummarySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()


class PublicProductListSerializer(serializers.Serializer):
    slug = serializers.SlugField(source="public_slug")
    name = serializers.CharField()
    brand = serializers.CharField(allow_blank=True)
    primary_category = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()
    from_price_cents = serializers.IntegerField(source="public_from_price_cents", min_value=0)
    has_active_sale = serializers.SerializerMethodField()
    variant_count = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()

    @extend_schema_field(PublicCategorySummarySerializer(allow_null=True))
    def get_primary_category(self, obj):
        links = getattr(obj, "public_category_links", ())
        primary = next((link for link in links if link.is_primary), None)
        category = primary.category if primary else (links[0].category if links else None)
        return {"name": category.name, "slug": category.slug} if category else None

    @extend_schema_field(PublicProductImageSerializer(allow_null=True))
    def get_primary_image(self, obj):
        image = next(iter(obj.images.all()), None)
        if image is None:
            return None
        return PublicProductImageSerializer(image, context=self.context).data

    @extend_schema_field(serializers.BooleanField())
    def get_has_active_sale(self, obj):
        return any(variant.active_price_cents != variant.selling_price_cents for variant in _public_variants(obj))

    @extend_schema_field(serializers.IntegerField(min_value=0))
    def get_variant_count(self, obj):
        return len(_public_variants(obj))

    @extend_schema_field(serializers.ChoiceField(choices=("available", "sold_out")))
    def get_availability(self, obj):
        return "available" if any(_available(variant) for variant in _public_variants(obj)) else "sold_out"


class PublicVariantSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    options = serializers.SerializerMethodField()
    price_cents = serializers.SerializerMethodField()
    sale_price_cents = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()

    @extend_schema_field(serializers.DictField(child=serializers.CharField()))
    def get_options(self, obj):
        return {
            assignment.option.name: assignment.value.value
            for assignment in obj.option_assignments.all()
        }

    @extend_schema_field(serializers.IntegerField(min_value=0))
    def get_price_cents(self, obj):
        return obj.active_price_cents

    @extend_schema_field(serializers.IntegerField(min_value=0, allow_null=True))
    def get_sale_price_cents(self, obj):
        return obj.sale_price_cents if obj.active_price_cents != obj.selling_price_cents else None

    @extend_schema_field(serializers.ChoiceField(choices=("available", "sold_out")))
    def get_availability(self, obj):
        return "available" if _available(obj) else "sold_out"


class PublicProductOptionSerializer(serializers.Serializer):
    name = serializers.CharField()
    values = serializers.ListField(child=serializers.CharField())


class PublicProductDetailSerializer(PublicProductListSerializer):
    description = serializers.CharField(allow_blank=True)
    categories = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()
    variants = PublicVariantSerializer(source="public_variants", many=True)
    request_url = serializers.SerializerMethodField()

    @extend_schema_field(PublicCategorySummarySerializer(many=True))
    def get_categories(self, obj):
        return [
            {"name": link.category.name, "slug": link.category.slug}
            for link in getattr(obj, "public_category_links", ())
        ]

    @extend_schema_field(PublicProductImageSerializer(many=True))
    def get_images(self, obj):
        return PublicProductImageSerializer(obj.images.all(), many=True, context=self.context).data

    @extend_schema_field(PublicProductOptionSerializer(many=True))
    def get_options(self, obj):
        used_values = {
            assignment.value_id
            for variant in _public_variants(obj)
            for assignment in variant.option_assignments.all()
        }
        return [
            {
                "name": option.name,
                "values": [
                    value.value for value in option.values.all() if value.id in used_values
                ],
            }
            for option in obj.options.all()
            if any(value.id in used_values for value in option.values.all())
        ]

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_request_url(self, obj):
        settings = self.context.get("business_settings")
        digits = whatsapp_digits(settings.whatsapp_phone) if settings is not None else ""
        if not 8 <= len(digits) <= 15:
            return None
        message = quote(
            f"Hello, I would like to request {obj.name} ({obj.public_slug})."
        )
        return f"https://wa.me/{digits}?text={message}"
