from rest_framework import generics
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from catalog.models import ProductVariant
from catalog.selectors.product import variant_queryset
from catalog.serializers.product_variant import (
    ProductVariantPricingSerializer,
    ProductVariantSerializer,
)
from catalog.services.pricing import update_variant_pricing


class ProductVariantListView(generics.ListAPIView):
    serializer_class = ProductVariantSerializer
    filterset_fields = ("product", "is_active")
    search_fields = ("sku", "product__name", "product__brand")
    ordering_fields = ("sku", "selling_price_cents", "created_at", "updated_at")
    ordering = ("product_id", "sku")

    def get_queryset(self):
        return variant_queryset()


class ProductVariantDetailView(generics.RetrieveAPIView):
    queryset = variant_queryset()
    serializer_class = ProductVariantSerializer


class ProductVariantPricingView(GenericAPIView):
    serializer_class = ProductVariantPricingSerializer
    def patch(self, request, pk):
        variant = generics.get_object_or_404(ProductVariant, pk=pk)
        serializer = ProductVariantPricingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        variant = update_variant_pricing(
            variant=variant,
            changes=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        variant = variant_queryset().get(pk=variant.pk)
        return Response(ProductVariantSerializer(variant).data)
