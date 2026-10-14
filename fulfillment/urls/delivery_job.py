from django.urls import path

from fulfillment.views.delivery_job import (
    DeliveryDeliverView, DeliveryFailView, DeliveryJobDetailView,
    DeliveryJobListCreateView, DeliveryStartView,
)

urlpatterns = [
    path("", DeliveryJobListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", DeliveryJobDetailView.as_view(), name="detail"),
    path("<uuid:pk>/start/", DeliveryStartView.as_view(), name="start"),
    path("<uuid:pk>/deliver/", DeliveryDeliverView.as_view(), name="deliver"),
    path("<uuid:pk>/fail/", DeliveryFailView.as_view(), name="fail"),
]
