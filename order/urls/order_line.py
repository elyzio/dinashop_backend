from django.urls import path

from order.views.order_line import OrderLineDetailView, OrderLineListView, OrderLineReceiveView

urlpatterns = [
    path("", OrderLineListView.as_view(), name="list"),
    path("<uuid:pk>/", OrderLineDetailView.as_view(), name="detail"),
    path("<uuid:pk>/receive/", OrderLineReceiveView.as_view(), name="receive"),
]
