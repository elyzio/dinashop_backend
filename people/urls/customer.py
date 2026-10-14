from django.urls import path

from people.views.customer import (
    CustomerDeactivateView, CustomerDetailView, CustomerListCreateView,
    CustomerReactivateView,
)

urlpatterns = [
    path("", CustomerListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", CustomerDetailView.as_view(), name="detail"),
    path("<uuid:pk>/deactivate/", CustomerDeactivateView.as_view(), name="deactivate"),
    path("<uuid:pk>/reactivate/", CustomerReactivateView.as_view(), name="reactivate"),
]
