from rest_framework import serializers


class PublicCategorySerializer(serializers.Serializer):
    name = serializers.CharField()
    slug = serializers.SlugField()
    parent_slug = serializers.SlugField(allow_null=True)
    sort_order = serializers.IntegerField(min_value=0)
    product_count = serializers.IntegerField(min_value=0)
