from django.urls import path

from payment.views.payment import PaymentDetailView, PaymentListView, PaymentReceiptView, PaymentRecordView

urlpatterns = [
    path("", PaymentListView.as_view(), name="list"),
    path("record/", PaymentRecordView.as_view(), name="record"),
    path("<uuid:pk>/", PaymentDetailView.as_view(), name="detail"),
    path("<uuid:pk>/receipt/", PaymentReceiptView.as_view(), name="receipt"),
]
