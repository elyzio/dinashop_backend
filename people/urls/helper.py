from django.urls import path

from people.views.helper import (
    HelperDeactivateView, HelperDetailView, HelperListCreateView,
    HelperReactivateView,
)

urlpatterns = [
    path("", HelperListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", HelperDetailView.as_view(), name="detail"),
    path("<uuid:pk>/deactivate/", HelperDeactivateView.as_view(), name="deactivate"),
    path("<uuid:pk>/reactivate/", HelperReactivateView.as_view(), name="reactivate"),
]
