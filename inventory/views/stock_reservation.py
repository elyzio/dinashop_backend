from rest_framework import generics

from inventory.selectors.inventory import reservation_queryset
from inventory.serializers.stock_reservation import StockReservationSerializer


class StockReservationListView(generics.ListAPIView):
    queryset = reservation_queryset()
    serializer_class = StockReservationSerializer
    filterset_fields = ("variant", "status", "order_line", "order_line__order")
    search_fields = ("variant__sku", "order_line__order__number")
    ordering_fields = ("created_at", "released_at", "consumed_at")
    ordering = ("-created_at",)


class StockReservationDetailView(generics.RetrieveAPIView):
    queryset = reservation_queryset()
    serializer_class = StockReservationSerializer
