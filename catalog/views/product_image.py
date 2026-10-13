from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from catalog.models import ProductImage
from catalog.serializers.product_image import (
    ProductImageMetadataSerializer,
    ProductImageReorderSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
)
from catalog.services.image import (
    create_product_image,
    delete_product_image,
    reorder_product_images,
    update_product_image_metadata,
)


class ProductImageListCreateView(generics.ListCreateAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ProductImageSerializer
    ordering_fields = ("sort_order", "created_at")
    ordering = ("sort_order", "created_at")

    def get_queryset(self):
        queryset = ProductImage.objects.select_related("product")
        product_id = self.request.query_params.get("product_id")
        return queryset.filter(product_id=product_id) if product_id else queryset

    def create(self, request, *args, **kwargs):
        serializer = ProductImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        image = create_product_image(
            product=data["product"],
            uploaded_file=data["image"],
            alt_text=data.get("alt_text", ""),
            sort_order=data.get("sort_order"),
            actor=request.user,
            request=request,
        )
        return Response(
            ProductImageSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProductImageDetailView(generics.RetrieveAPIView):
    queryset = ProductImage.objects.select_related("product")
    serializer_class = ProductImageSerializer

    def patch(self, request, *args, **kwargs):
        image = self.get_object()
        serializer = ProductImageMetadataSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        image = update_product_image_metadata(
            image=image,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(ProductImageSerializer(image, context={"request": request}).data)

    def delete(self, request, *args, **kwargs):
        delete_product_image(image=self.get_object(), actor=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductImageReorderView(GenericAPIView):
    serializer_class = ProductImageReorderSerializer
    def post(self, request):
        serializer = ProductImageReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        images = reorder_product_images(
            product=serializer.validated_data["product"],
            image_ids=serializer.validated_data["image_ids"],
            actor=request.user,
            request=request,
        )
        return Response(
            ProductImageSerializer(images, many=True, context={"request": request}).data
        )
