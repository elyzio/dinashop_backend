from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from custom.models import BusinessSettings
from dina_shop.api.utils import parse_idempotency_key
from order.models import Order
from order.selectors.order import order_queryset
from order.serializers.order import (
    CancelOrderSerializer, CustomerNotifiedSerializer, DeclineOrderSerializer,
    OrderCreateSerializer, OrderReadSerializer, SetFinalPriceSerializer,
    SpecialTransitionSerializer, VersionSerializer,
)
from order.services.totals import payment_status
from order.services.workflow import (
    cancel_order, complete_order, create_order, fulfill_order,
    mark_customer_notified, set_final_price, transition_special_order,
)


def _fresh(order_id):
    return order_queryset().get(pk=order_id)


class OrderListCreateView(generics.ListCreateAPIView):
    search_fields = ("number", "customer_name", "customer_phone", "lines__description", "lines__sku")
    ordering_fields = ("created_at", "updated_at", "number")
    ordering = ("-created_at",)

    def get_queryset(self):
        queryset = order_queryset()
        params = self.request.query_params
        if params.get("type") == "special":
            queryset = queryset.exclude(special_status__isnull=True)
        elif params.get("type") == "ordinary":
            queryset = queryset.filter(special_status__isnull=True)
        for parameter, field in (
            ("status", "status"), ("special_status", "special_status"),
            ("delivery_method", "delivery_method"), ("customer_id", "customer_id"),
        ):
            if params.get(parameter):
                queryset = queryset.filter(**{field: params[parameter]})
        if params.get("from"):
            queryset = queryset.filter(created_at__date__gte=params["from"])
        if params.get("to"):
            queryset = queryset.filter(created_at__date__lte=params["to"])
        if params.get("payment_status"):
            matching = [item.id for item in queryset if payment_status(item) == params["payment_status"]]
            queryset = order_queryset().filter(id__in=matching)
        return queryset.distinct()

    def get_serializer_class(self):
        return OrderCreateSerializer if self.request.method == "POST" else OrderReadSerializer

    def create(self, request, *args, **kwargs):
        key = parse_idempotency_key(request)
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order, replayed = create_order(
            data=serializer.validated_data, idempotency_key=key,
            actor=request.user, request=request,
        )
        return Response(
            {"order": OrderReadSerializer(_fresh(order.id)).data, "replayed": replayed},
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )


class OrderDetailView(generics.RetrieveAPIView):
    queryset = order_queryset()
    serializer_class = OrderReadSerializer


class OrderCommandView(GenericAPIView):
    queryset = Order.objects.all()
    serializer_class = VersionSerializer
    service = None

    def service_kwargs(self, data):
        return {"version": data["version"]}

    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.service(
            order=self.get_object(), actor=request.user, request=request,
            **self.service_kwargs(serializer.validated_data),
        )
        return Response(OrderReadSerializer(_fresh(order.id)).data)


class OrderCancelView(OrderCommandView):
    serializer_class = CancelOrderSerializer
    service = staticmethod(cancel_order)

    def service_kwargs(self, data):
        return {"version": data["version"], "reason": data["reason"]}


class OrderFulfillView(OrderCommandView):
    service = staticmethod(fulfill_order)


class OrderCompleteView(OrderCommandView):
    service = staticmethod(complete_order)


class OrderSpecialTransitionView(OrderCommandView):
    serializer_class = SpecialTransitionSerializer
    service = staticmethod(transition_special_order)

    def service_kwargs(self, data):
        return {"version": data["version"], "target": data["target"]}


class OrderFinalPriceView(OrderCommandView):
    serializer_class = SetFinalPriceSerializer
    service = staticmethod(set_final_price)

    def service_kwargs(self, data):
        return data


class OrderCustomerNotifiedView(OrderCommandView):
    serializer_class = CustomerNotifiedSerializer
    service = staticmethod(mark_customer_notified)

    def service_kwargs(self, data):
        return {
            "version": data["version"],
            "accepted_price_change": data.get("accepted_price_change"),
        }


class OrderDeclineView(OrderCommandView):
    serializer_class = DeclineOrderSerializer

    def post(self, request, pk):
        from payment.services.refund import decline_special_order

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = decline_special_order(
            order=self.get_object(), data=serializer.validated_data,
            actor=request.user, request=request,
        )
        return Response(OrderReadSerializer(_fresh(order.id)).data)


class OrderReceiptView(GenericAPIView):
    queryset = order_queryset()
    serializer_class = OrderReadSerializer

    def get(self, request, pk):
        from payment.serializers.payment import PaymentReadSerializer
        from payment.serializers.refund import RefundReadSerializer

        order = self.get_object()
        settings = BusinessSettings.objects.filter(key="default").first()
        return Response({
            "order": OrderReadSerializer(order).data,
            "payments": PaymentReadSerializer(order.payments.all(), many=True).data,
            "refunds": RefundReadSerializer(order.refunds.all(), many=True).data,
            "business_settings": {
                "business_name": settings.business_name,
                "address": settings.address,
                "phone": settings.phone,
                "registration_id": settings.registration_id,
                "receipt_footer": settings.receipt_footer,
                "currency": settings.currency,
                "timezone": settings.timezone,
            } if settings else None,
        })
