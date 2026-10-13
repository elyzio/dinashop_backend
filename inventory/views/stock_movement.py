from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from dina_shop.api.utils import parse_idempotency_key
from inventory.selectors.inventory import balance_queryset, movement_queryset
from inventory.serializers.inventory_balance import InventoryBalanceSerializer
from inventory.serializers.stock_movement import (
    StockAdjustmentSerializer,
    StockMovementSerializer,
    StockReceiptSerializer,
)
from inventory.services.stock import adjust_stock, receive_stock


def _command_response(movement, balance, *, replayed=False):
    return {
        "movement": StockMovementSerializer(movement).data,
        "balance": InventoryBalanceSerializer(balance).data,
        "replayed": replayed,
    }


class StockMovementListView(generics.ListAPIView):
    serializer_class = StockMovementSerializer
    filterset_fields = ("variant", "movement_type", "order", "recorded_by")
    search_fields = ("variant__sku", "variant__product__name", "reference", "note")
    ordering_fields = ("created_at", "quantity_delta", "landed_cost_cents")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = movement_queryset()
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        return queryset


class StockMovementDetailView(generics.RetrieveAPIView):
    queryset = movement_queryset()
    serializer_class = StockMovementSerializer


class StockReceiptView(GenericAPIView):
    serializer_class = StockReceiptSerializer
    def post(self, request):
        idempotency_key = parse_idempotency_key(request)
        serializer = StockReceiptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement, balance, replayed = receive_stock(
            data=serializer.validated_data,
            idempotency_key=idempotency_key,
            actor=request.user,
            request=request,
        )
        balance = balance_queryset().get(pk=balance.pk)
        return Response(
            _command_response(movement, balance, replayed=replayed),
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class StockAdjustmentView(GenericAPIView):
    serializer_class = StockAdjustmentSerializer
    def post(self, request):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement, balance = adjust_stock(
            data=serializer.validated_data,
            actor=request.user,
            request=request,
        )
        balance = balance_queryset().get(pk=balance.pk)
        return Response(
            _command_response(movement, balance),
            status=status.HTTP_201_CREATED,
        )
