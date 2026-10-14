from django.urls import include, path

app_name = "payment"

urlpatterns = [
    path("payment/", include(("payment.urls.payment", "payment"), namespace="payment")),
    path("refund/", include(("payment.urls.refund", "refund"), namespace="refund")),
    path("refund-line/", include(("payment.urls.refund_line", "refund-line"), namespace="refund-line")),
    path("cod-handover/", include(("payment.urls.cod_handover", "cod-handover"), namespace="cod-handover")),
]
