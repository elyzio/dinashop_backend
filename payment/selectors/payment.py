from payment.models import CodHandover, Payment, Refund, RefundLine


def payment_queryset():
    return Payment.objects.select_related("order", "received_by")


def refund_queryset():
    return Refund.objects.select_related(
        "order", "payment", "processed_by",
    ).prefetch_related("lines__order_line", "lines__returned_variant")


def refund_line_queryset():
    return RefundLine.objects.select_related(
        "refund", "order_line", "returned_variant",
    )


def cod_handover_queryset():
    return CodHandover.objects.select_related("helper", "order", "recorded_by")
