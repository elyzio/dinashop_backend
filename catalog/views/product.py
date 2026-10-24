from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from django.db.models import F, IntegerField, Min, Q, Sum, Value
from django.db.models.functions import Coalesce

from catalog.models import Product
from catalog.selectors.product import product_card_queryset, product_queryset
from catalog.serializers.product import (
    ProductCreateSerializer,
    ProductListSerializer,
    ProductReadSerializer,
    ProductUpdateSerializer,
    ProductVariantGridSerializer,
    ProductVisibilitySerializer,
)
from catalog.services.product import (
    create_product,
    replace_variant_grid,
    update_product,
    update_product_visibility,
)


def _fresh_product(product_id):
    return product_queryset().get(pk=product_id)


class ProductListCreateView(generics.ListCreateAPIView):
    search_fields = ("name", "brand", "description", "variants__sku")
    ordering_fields = ("name", "brand", "created_at", "updated_at", "display_price", "available_quantity")
    ordering = ("name",)

    def get_queryset(self):
        queryset = (product_queryset() if self.request.query_params.get("detail") == "1" else product_card_queryset()).annotate(
            available_quantity_db=Coalesce(
                Sum(
                    F("variants__inventory__in_hand") - F("variants__inventory__promised"),
                    filter=Q(variants__is_active=True),
                ),
                Value(0),
                output_field=IntegerField(),
            ),
            display_price=Min(
                "variants__selling_price_cents",
                filter=Q(variants__is_active=True),
            ),
        )
        visibility = self.request.query_params.get("visibility")
        category_id = self.request.query_params.get("category_id")
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        if category_id:
            queryset = queryset.filter(category_links__category_id=category_id).distinct()
        availability = self.request.query_params.get("availability")
        if availability == "available":
            queryset = queryset.filter(visibility="active", available_quantity_db__gt=5)
        elif availability == "low":
            queryset = queryset.filter(visibility="active", available_quantity_db__gte=1, available_quantity_db__lte=5)
        elif availability == "sold_out":
            queryset = queryset.filter(visibility="active", available_quantity_db__lte=0)
        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductCreateSerializer
        return ProductReadSerializer if self.request.query_params.get("detail") == "1" else ProductListSerializer

    def create(self, request, *args, **kwargs):
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = create_product(
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        product = _fresh_product(product.id)
        return Response(
            ProductReadSerializer(product, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProductDetailView(generics.RetrieveUpdateAPIView):
    queryset = product_queryset()

    def get_serializer_class(self):
        return ProductUpdateSerializer if self.request.method in ("PUT", "PATCH") else ProductReadSerializer

    def update(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = ProductUpdateSerializer(
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        product = update_product(
            product=product,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        product = _fresh_product(product.id)
        return Response(ProductReadSerializer(product, context={"request": request}).data)


class ProductVariantGridView(GenericAPIView):
    serializer_class = ProductVariantGridSerializer
    def put(self, request, pk):
        product = generics.get_object_or_404(Product, pk=pk)
        serializer = ProductVariantGridSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = replace_variant_grid(
            product=product,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        product = _fresh_product(product.id)
        return Response(ProductReadSerializer(product, context={"request": request}).data)


class ProductVisibilityView(GenericAPIView):
    serializer_class = ProductVisibilitySerializer
    def post(self, request, pk):
        product = generics.get_object_or_404(Product, pk=pk)
        serializer = ProductVisibilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = update_product_visibility(
            product=product,
            visibility=serializer.validated_data["visibility"],
            actor=request.user,
            request=request,
        )
        product = _fresh_product(product.id)
        return Response(ProductReadSerializer(product, context={"request": request}).data)
