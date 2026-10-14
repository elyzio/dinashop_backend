from django.db.models import Prefetch

from order.models import Order, OrderLine
from payment.models import Refund


def order_queryset():
    refunds = Refund.objects.select_related("payment", "processed_by").prefetch_related("lines")
    return Order.objects.select_related(
        "customer", "created_by", "delivery_job", "delivery_job__helper",
        "delivery_job__cod_payment",
    ).prefetch_related(
        "lines__variant__product",
        "lines__variant__option_values__option",
        "lines__reservation",
        "payments__received_by",
        Prefetch("refunds", queryset=refunds),
    )


def order_line_queryset():
    return OrderLine.objects.select_related(
        "order", "variant", "variant__product", "reservation",
    ).prefetch_related("variant__option_values__option")
