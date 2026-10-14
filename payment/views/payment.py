from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from custom.models import BusinessSettings
from dina_shop.api.utils import parse_idempotency_key
from order.selectors.order import order_queryset
from order.serializers.order import OrderReadSerializer
from payment.models import Payment
from payment.selectors.payment import payment_queryset
from payment.serializers.payment import PaymentReadSerializer, PaymentRecordSerializer
from payment.services.payment import record_payment


def receipt_settings():
    item = BusinessSettings.objects.filter(key="default").first()
    if item is None:
        return None
    return {
        "business_name": item.business_name, "address": item.address,
        "phone": item.phone, "registration_id": item.registration_id,
        "receipt_footer": item.receipt_footer, "currency": item.currency,
        "timezone": item.timezone,
    }


class PaymentListView(generics.ListAPIView):
    queryset = payment_queryset()
    serializer_class = PaymentReadSerializer
    filterset_fields = ("order", "method", "received_by")
    search_fields = ("receipt_number", "order__number", "external_reference", "received_by_name")
    ordering_fields = ("occurred_at", "created_at", "amount_cents")
    ordering = ("-occurred_at",)

    def get_queryset(self):
        queryset = payment_queryset()
        if self.request.query_params.get("from"):
            queryset = queryset.filter(occurred_at__date__gte=self.request.query_params["from"])
        if self.request.query_params.get("to"):
            queryset = queryset.filter(occurred_at__date__lte=self.request.query_params["to"])
        return queryset


class PaymentDetailView(generics.RetrieveAPIView):
    queryset = payment_queryset()
    serializer_class = PaymentReadSerializer


class PaymentRecordView(GenericAPIView):
    serializer_class = PaymentRecordSerializer

    def post(self, request):
        key = parse_idempotency_key(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        order = data.pop("order")
        version = data.pop("order_version")
        payment, replayed = record_payment(
            order=order, order_version=version, data=data,
            idempotency_key=key, actor=request.user, request=request,
        )
        return Response(
            {"payment": PaymentReadSerializer(payment_queryset().get(pk=payment.pk)).data, "replayed": replayed},
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class PaymentReceiptView(GenericAPIView):
    queryset = payment_queryset()
    serializer_class = PaymentReadSerializer

    def get(self, request, pk):
        payment = self.get_object()
        order = order_queryset().get(pk=payment.order_id)
        return Response({
            "payment": PaymentReadSerializer(payment).data,
            "order": OrderReadSerializer(order).data,
            "business_settings": receipt_settings(),
        })
