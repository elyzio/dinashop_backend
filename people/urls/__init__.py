from django.urls import include, path

app_name = "people"

urlpatterns = [
    path("customer/", include(("people.urls.customer", "customer"), namespace="customer")),
    path("helper/", include(("people.urls.helper", "helper"), namespace="helper")),
]
