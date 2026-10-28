from rest_framework import generics
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from drf_spectacular.utils import OpenApiParameter, extend_schema

from catalog.models import ProductVariant
from catalog.selectors.product import variant_queryset
from catalog.serializers.product_variant import (
    ProductVariantBarcodeGenerateSerializer,
    ProductVariantBarcodeLookupSerializer,
    ProductVariantPricingSerializer,
    ProductVariantSerializer,
)
from catalog.services.barcode import generate_variant_barcode
from catalog.services.pricing import update_variant_pricing
from dina_shop.api.exceptions import ConflictError


class ProductVariantListView(generics.ListAPIView):
    serializer_class = ProductVariantSerializer
    filterset_fields = ("product", "is_active")
    search_fields = ("sku", "barcode", "product__name", "product__brand")
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


class ProductVariantBarcodeGenerateView(GenericAPIView):
    serializer_class = ProductVariantBarcodeGenerateSerializer

    @extend_schema(request=None, responses=ProductVariantSerializer)
    def post(self, request, pk):
        variant = generics.get_object_or_404(ProductVariant, pk=pk)
        variant = generate_variant_barcode(
            variant=variant,
            actor=request.user,
            request=request,
        )
        variant = variant_queryset().get(pk=variant.pk)
        return Response(ProductVariantSerializer(variant).data)


class ProductVariantBarcodeLookupView(GenericAPIView):
    serializer_class = ProductVariantBarcodeLookupSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="barcode",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses=ProductVariantBarcodeLookupSerializer,
    )
    def get(self, request):
        barcode = request.query_params.get("barcode", "").strip()
        if not barcode:
            raise ValidationError({"barcode": "Enter a barcode."})
        variant = (
            variant_queryset()
            .prefetch_related("product__images__renditions")
            .filter(barcode=barcode)
            .first()
        )
        if variant is None:
            raise NotFound("No variant uses this barcode.", code="barcode_not_found")
        if not variant.is_active or variant.product.visibility != "active":
            raise ConflictError(
                "This barcode belongs to a variant that is not available for sale.",
                code="variant_not_sellable",
            )
        if variant.inventory.available <= 0:
            raise ConflictError(
                "This barcode belongs to a sold-out variant.",
                code="sold_out",
            )
        return Response(
            ProductVariantBarcodeLookupSerializer(
                variant,
                context={"request": request},
            ).data
        )
