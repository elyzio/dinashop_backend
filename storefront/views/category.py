from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from storefront.selectors.catalog import public_category_records
from storefront.serializers.category import PublicCategorySerializer

from .base import PublicStorefrontViewMixin


class PublicCategoryListView(PublicStorefrontViewMixin, GenericAPIView):
    serializer_class = PublicCategorySerializer
    # This endpoint serializes a computed list rather than a model queryset.
    # GenericAPIView is also inspected by DRF's default filter/schema tools,
    # which call get_queryset().  Providing it prevents an AssertionError on
    # those requests while keeping the public response intentionally
    # unpaginated (the category set is small and used as filter metadata).
    filter_backends = []
    pagination_class = None

    def get_queryset(self):
        return public_category_records()

    def get(self, request):
        return Response(self.get_serializer(self.get_queryset(), many=True).data)
