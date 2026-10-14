from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from dina_shop.api.utils import parse_idempotency_key
from inventory.serializers.stock_movement import StockMovementSerializer
from order.models import OrderLine
from order.selectors.order import order_line_queryset
from order.serializers.order_line import OrderLineReadSerializer, SpecialLineReceiveSerializer
from order.services.special import receive_special_line


class OrderLineListView(generics.ListAPIView):
    queryset = order_line_queryset()
    serializer_class = OrderLineReadSerializer
    filterset_fields = ("order", "kind", "variant")
    search_fields = ("order__number", "product_name", "description", "sku")
    ordering_fields = ("created_at", "quantity", "unit_price_cents")
    ordering = ("created_at",)


class OrderLineDetailView(generics.RetrieveAPIView):
    queryset = order_line_queryset()
    serializer_class = OrderLineReadSerializer


class OrderLineReceiveView(GenericAPIView):
    queryset = OrderLine.objects.all()
    serializer_class = SpecialLineReceiveSerializer

    def post(self, request, pk):
        key = parse_idempotency_key(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        line, movement, replayed = receive_special_line(
            line=self.get_object(), data=serializer.validated_data,
            idempotency_key=key, actor=request.user, request=request,
        )
        return Response(
            {
                "order_line": OrderLineReadSerializer(order_line_queryset().get(pk=line.pk)).data,
                "movement": StockMovementSerializer(movement).data,
                "replayed": replayed,
            },
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )
