from rest_framework import generics

from custom.models import AuditEvent
from custom.serializers.audit_event import AuditEventSerializer


class AuditEventListView(generics.ListAPIView):
    serializer_class = AuditEventSerializer
    filterset_fields = ("actor", "action", "entity_type", "entity_id")
    search_fields = ("action", "entity_type", "entity_id")
    ordering_fields = ("created_at",)
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = AuditEvent.objects.select_related("actor")
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        return queryset


class AuditEventDetailView(generics.RetrieveAPIView):
    queryset = AuditEvent.objects.select_related("actor")
    serializer_class = AuditEventSerializer
