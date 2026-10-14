from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from dina_shop.api.utils import parse_idempotency_key
from fulfillment.models import DeliveryJob
from fulfillment.selectors.delivery import delivery_job_queryset
from fulfillment.serializers.delivery_job import (
    DeliveryFailSerializer, DeliveryJobCreateSerializer,
    DeliveryJobReadSerializer, DeliveryVersionSerializer,
)
from fulfillment.services.delivery import create_delivery_job, deliver_order, fail_delivery, start_delivery


class DeliveryJobListCreateView(generics.ListCreateAPIView):
    search_fields = ("order__number", "order__customer_name", "order__delivery_address", "helper__name")
    filterset_fields = ("status", "helper", "order")
    ordering_fields = ("created_at", "updated_at", "status_changed_at", "fee_cents", "fuel_cents")
    ordering = ("-created_at",)

    def get_queryset(self):
        return delivery_job_queryset()

    def get_serializer_class(self):
        return DeliveryJobCreateSerializer if self.request.method == "POST" else DeliveryJobReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = DeliveryJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = create_delivery_job(data=serializer.validated_data, actor=request.user, request=request)
        return Response(
            DeliveryJobReadSerializer(delivery_job_queryset().get(pk=job.pk)).data,
            status=status.HTTP_201_CREATED,
        )


class DeliveryJobDetailView(generics.RetrieveAPIView):
    queryset = delivery_job_queryset()
    serializer_class = DeliveryJobReadSerializer


class DeliveryCommandView(GenericAPIView):
    queryset = DeliveryJob.objects.all()
    serializer_class = DeliveryVersionSerializer
    service = None

    def service_kwargs(self, data):
        return {"order_version": data["order_version"]}

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job, replayed = self.service(
            job=self.get_object(), actor=request.user, request=request,
            **self.service_kwargs(serializer.validated_data),
        )
        return Response({
            "delivery_job": DeliveryJobReadSerializer(delivery_job_queryset().get(pk=job.pk)).data,
            "replayed": replayed,
        })


class DeliveryStartView(DeliveryCommandView):
    service = staticmethod(start_delivery)


class DeliveryDeliverView(DeliveryCommandView):
    service = staticmethod(deliver_order)

    def post(self, request, pk):
        self.idempotency_key = parse_idempotency_key(request)
        return super().post(request, pk)

    def service_kwargs(self, data):
        return {"order_version": data["order_version"], "idempotency_key": self.idempotency_key}


class DeliveryFailView(DeliveryCommandView):
    serializer_class = DeliveryFailSerializer
    service = staticmethod(fail_delivery)

    def service_kwargs(self, data):
        return {"order_version": data["order_version"], "failure_reason": data["failure_reason"]}
