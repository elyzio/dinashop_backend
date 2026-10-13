from rest_framework import generics

from catalog.models import PriceHistory
from catalog.serializers.price_history import PriceHistorySerializer


class PriceHistoryListView(generics.ListAPIView):
    queryset = PriceHistory.objects.select_related("variant", "changed_by")
    serializer_class = PriceHistorySerializer
    filterset_fields = ("variant", "kind", "changed_by")
    ordering_fields = ("changed_at",)
    ordering = ("-changed_at",)

    def get_queryset(self):
        queryset = self.queryset
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if from_date:
            queryset = queryset.filter(changed_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(changed_at__date__lte=to_date)
        return queryset


class PriceHistoryDetailView(generics.RetrieveAPIView):
    queryset = PriceHistory.objects.select_related("variant", "changed_by")
    serializer_class = PriceHistorySerializer
