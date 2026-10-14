from django.urls import path

from payment.views.refund import RefundLineDetailView, RefundLineListView

urlpatterns = [
    path("", RefundLineListView.as_view(), name="list"),
    path("<uuid:pk>/", RefundLineDetailView.as_view(), name="detail"),
]
