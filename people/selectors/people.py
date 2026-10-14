from django.db.models import Prefetch

from fulfillment.models import DeliveryJob
from order.models import Order
from people.models import Customer, Helper


def customer_queryset():
    orders = Order.objects.prefetch_related("lines", "payments", "refunds")
    return Customer.objects.prefetch_related(Prefetch("orders", queryset=orders))


def helper_queryset():
    jobs = DeliveryJob.objects.select_related("order", "cod_payment")
    return Helper.objects.prefetch_related(
        Prefetch("delivery_jobs", queryset=jobs),
        "cod_handovers",
    )
