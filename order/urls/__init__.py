from django.urls import include, path

app_name = "order"

urlpatterns = [
    path("order/", include(("order.urls.order", "order"), namespace="order")),
    path("order-line/", include(("order.urls.order_line", "order-line"), namespace="order-line")),
]
