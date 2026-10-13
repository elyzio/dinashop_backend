from rest_framework import generics

from inventory.selectors.inventory import balance_queryset
from inventory.serializers.inventory_balance import InventoryBalanceSerializer


class InventoryBalanceListView(generics.ListAPIView):
    serializer_class = InventoryBalanceSerializer
    filterset_fields = ("variant", "variant__product")
    search_fields = ("variant__sku", "variant__product__name", "variant__product__brand")
    ordering_fields = ("in_hand", "promised", "last_landed_cost_cents", "updated_at")
    ordering = ("variant__product__name", "variant__sku")

    def get_queryset(self):
        queryset = balance_queryset()
        status_value = self.request.query_params.get("status")
        if status_value == "available":
            queryset = queryset.filter(in_hand__gt=0)
        elif status_value == "out_of_stock":
            queryset = queryset.filter(in_hand=0)
        return queryset


class InventoryBalanceDetailView(generics.RetrieveAPIView):
    queryset = balance_queryset()
    serializer_class = InventoryBalanceSerializer
