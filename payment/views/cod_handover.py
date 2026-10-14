from django.db.models import Sum
from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from dina_shop.api.utils import parse_idempotency_key
from fulfillment.models import DeliveryJob
from payment.models import CodHandover
from payment.selectors.payment import cod_handover_queryset
from payment.serializers.cod_handover import CodHandoverReadSerializer, CodHandoverRecordSerializer
from payment.services.cod import record_cod_handover


class CodHandoverListView(generics.ListAPIView):
    queryset = cod_handover_queryset()
    serializer_class = CodHandoverReadSerializer
    filterset_fields = ("helper", "order", "recorded_by")
    search_fields = ("helper__name", "order__number")
    ordering_fields = ("handed_over_at", "created_at", "amount_cents")
    ordering = ("-handed_over_at",)

    def get_queryset(self):
        queryset = cod_handover_queryset()
        if self.request.query_params.get("from"):
            queryset = queryset.filter(handed_over_at__date__gte=self.request.query_params["from"])
        if self.request.query_params.get("to"):
            queryset = queryset.filter(handed_over_at__date__lte=self.request.query_params["to"])
        return queryset


class CodHandoverDetailView(generics.RetrieveAPIView):
    queryset = cod_handover_queryset()
    serializer_class = CodHandoverReadSerializer


class CodHandoverRecordView(GenericAPIView):
    serializer_class = CodHandoverRecordSerializer

    def post(self, request):
        key = parse_idempotency_key(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        handover, replayed = record_cod_handover(
            data=serializer.validated_data, idempotency_key=key,
            actor=request.user, request=request,
        )
        return Response(
            {"handover": CodHandoverReadSerializer(cod_handover_queryset().get(pk=handover.pk)).data, "replayed": replayed},
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class CodHandoverSummaryView(GenericAPIView):
    serializer_class = CodHandoverReadSerializer

    def get(self, request):
        jobs = DeliveryJob.objects.filter(
            status=DeliveryJob.Status.DELIVERED,
            cod_payment__isnull=False,
        ).select_related("helper", "order", "cod_payment")
        if request.query_params.get("helper_id"):
            jobs = jobs.filter(helper_id=request.query_params["helper_id"])
        rows = []
        for job in jobs:
            handed = CodHandover.objects.filter(
                helper=job.helper, order=job.order,
            ).aggregate(total=Sum("amount_cents"))["total"] or 0
            rows.append({
                "helper_id": str(job.helper_id), "helper_name": job.helper.name,
                "order_id": str(job.order_id), "order_number": job.order.number,
                "collected_cents": job.cod_payment.amount_cents,
                "handed_over_cents": handed,
                "held_cents": max(0, job.cod_payment.amount_cents - handed),
            })
        return Response({
            "collected_cents": sum(row["collected_cents"] for row in rows),
            "handed_over_cents": sum(row["handed_over_cents"] for row in rows),
            "held_cents": sum(row["held_cents"] for row in rows),
            "results": rows,
        })
