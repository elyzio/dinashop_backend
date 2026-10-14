from fulfillment.models import DeliveryJob


def delivery_job_queryset():
    return DeliveryJob.objects.select_related(
        "order", "order__customer", "helper", "created_by", "updated_by", "cod_payment",
    )
