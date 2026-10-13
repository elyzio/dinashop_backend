from rest_framework import generics, status
from rest_framework.response import Response

from custom.selectors.category import category_queryset
from custom.serializers.category import CategoryReadSerializer, CategoryWriteSerializer
from custom.services.category import create_category, delete_category, update_category


class CategoryListCreateView(generics.ListCreateAPIView):
    queryset = category_queryset()
    filterset_fields = ("status", "parent_id")
    search_fields = ("name", "slug")
    ordering_fields = ("name", "sort_order", "created_at", "updated_at")
    ordering = ("sort_order", "name")

    def get_serializer_class(self):
        return CategoryWriteSerializer if self.request.method == "POST" else CategoryReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = CategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = create_category(
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(CategoryReadSerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = category_queryset()

    def get_serializer_class(self):
        return CategoryWriteSerializer if self.request.method in ("PUT", "PATCH") else CategoryReadSerializer

    def update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = CategoryWriteSerializer(
            category,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        category = update_category(
            category=category,
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        return Response(CategoryReadSerializer(category).data)

    def destroy(self, request, *args, **kwargs):
        delete_category(category=self.get_object(), actor=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)
