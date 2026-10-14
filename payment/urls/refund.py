from django.urls import path

from payment.views.refund import RefundCreateView, RefundDetailView, RefundListView, RefundReceiptView

urlpatterns = [
    path("", RefundListView.as_view(), name="list"),
    path("create/", RefundCreateView.as_view(), name="create"),
    path("<uuid:pk>/", RefundDetailView.as_view(), name="detail"),
    path("<uuid:pk>/receipt/", RefundReceiptView.as_view(), name="receipt"),
]
