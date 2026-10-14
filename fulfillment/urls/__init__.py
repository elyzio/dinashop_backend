from django.urls import include, path

app_name = "fulfillment"

urlpatterns = [
    path("delivery-job/", include(("fulfillment.urls.delivery_job", "delivery-job"), namespace="delivery-job")),
]
