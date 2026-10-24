from rest_framework import serializers

from catalog.models import Product, ProductImage, ProductImageRendition


class ProductImageRenditionSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImageRendition
        fields = ("kind", "image_url", "width", "height", "file_size_bytes")
        read_only_fields = fields

    def get_image_url(self, obj) -> str | None:
        if not obj.image:
            return None
        url = obj.image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    renditions = ProductImageRenditionSerializer(many=True, read_only=True)

    class Meta:
        model = ProductImage
        fields = (
            "id",
            "product",
            "image",
            "image_url",
            "alt_text",
            "sort_order",
            "width",
            "height",
            "file_size_bytes",
            "renditions",
            "created_at",
        )
        read_only_fields = fields

    def get_image_url(self, obj) -> str | None:
        if not obj.image:
            return None
        url = obj.image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ProductImageUploadSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.all(),
    )
    image = serializers.ImageField()
    alt_text = serializers.CharField(max_length=240, allow_blank=True, required=False)
    sort_order = serializers.IntegerField(min_value=0, required=False)


class ProductImageMetadataSerializer(serializers.Serializer):
    alt_text = serializers.CharField(max_length=240, allow_blank=True, required=False)
    sort_order = serializers.IntegerField(min_value=0, required=False)


class ProductImageReorderSerializer(serializers.Serializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source="product",
        queryset=Product.objects.all(),
    )
    image_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
    )

    def validate_image_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Image IDs must be unique.")
        return value
