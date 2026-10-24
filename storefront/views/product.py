from django.db.models import Q
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from dina_shop.api.pagination import StandardPagination

from storefront.selectors.catalog import public_product_queryset
from storefront.serializers.product import (
    PublicProductDetailSerializer,
    PublicProductListSerializer,
)

from .base import PublicStorefrontViewMixin


class PublicPagination(StandardPagination):
    page_size = 24
    max_page_size = 48


class PublicProductListView(PublicStorefrontViewMixin, generics.ListAPIView):
    serializer_class = PublicProductListSerializer
    pagination_class = PublicPagination

    def get_queryset(self):
        queryset = public_product_queryset(
            category_slug=self.request.query_params.get("category") or None,
        )
        search = (self.request.query_params.get("search") or "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(brand__icontains=search)
            )
        ordering = self.request.query_params.get("ordering", "newest")
        ordering_map = {
            "newest": ("-created_at", "name"),
            "price_asc": ("public_from_price_cents", "name"),
            "price_desc": ("-public_from_price_cents", "name"),
            "name": ("name",),
        }
        if ordering not in ordering_map:
            raise ValidationError(
                {"ordering": "Use newest, price_asc, price_desc, or name."}
            )
        return queryset.order_by(*ordering_map[ordering])


class PublicProductDetailView(PublicStorefrontViewMixin, generics.RetrieveAPIView):
    serializer_class = PublicProductDetailSerializer
    lookup_field = "public_slug"

    def get_queryset(self):
        return public_product_queryset()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        from custom.models import BusinessSettings

        context["business_settings"] = BusinessSettings.objects.filter(key="default").first()
        return context
