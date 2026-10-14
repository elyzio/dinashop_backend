from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from dina_shop.api.utils import parse_idempotency_key
from order.selectors.order import order_queryset
from order.serializers.order import OrderReadSerializer
from payment.selectors.payment import refund_line_queryset, refund_queryset
from payment.serializers.payment import PaymentReadSerializer
from payment.serializers.refund import RefundCreateSerializer, RefundLineReadSerializer, RefundReadSerializer
from payment.services.refund import create_refund
from payment.views.payment import receipt_settings


class RefundListView(generics.ListAPIView):
    queryset = refund_queryset()
    serializer_class = RefundReadSerializer
    filterset_fields = ("order", "payment", "method", "processed_by")
    search_fields = ("number", "order__number", "reason", "processed_by_name")
    ordering_fields = ("created_at", "credit_cents", "cash_refund_cents")
    ordering = ("-created_at",)


class RefundDetailView(generics.RetrieveAPIView):
    queryset = refund_queryset()
    serializer_class = RefundReadSerializer


class RefundCreateView(GenericAPIView):
    serializer_class = RefundCreateSerializer

    def post(self, request):
        key = parse_idempotency_key(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        order = data.pop("order")
        version = data.pop("order_version")
        refund, replayed = create_refund(
            order=order, order_version=version, data=data,
            idempotency_key=key, actor=request.user, request=request,
        )
        return Response(
            {"refund": RefundReadSerializer(refund_queryset().get(pk=refund.pk)).data, "replayed": replayed},
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class RefundReceiptView(GenericAPIView):
    queryset = refund_queryset()
    serializer_class = RefundReadSerializer

    def get(self, request, pk):
        refund = self.get_object()
        order = order_queryset().get(pk=refund.order_id)
        return Response({
            "refund": RefundReadSerializer(refund).data,
            "order": OrderReadSerializer(order).data,
            "payments": PaymentReadSerializer(order.payments.all(), many=True).data,
            "business_settings": receipt_settings(),
        })


class RefundLineListView(generics.ListAPIView):
    queryset = refund_line_queryset()
    serializer_class = RefundLineReadSerializer
    filterset_fields = ("refund", "order_line", "disposition", "returned_variant")
    ordering_fields = ("quantity", "amount_cents")


class RefundLineDetailView(generics.RetrieveAPIView):
    queryset = refund_line_queryset()
    serializer_class = RefundLineReadSerializer
