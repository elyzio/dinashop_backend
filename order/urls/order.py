from django.urls import path

from order.views.order import (
    OrderCancelView, OrderCompleteView, OrderCustomerNotifiedView,
    OrderDeclineView, OrderDetailView, OrderFinalPriceView, OrderFulfillView,
    OrderListCreateView, OrderReceiptView, OrderSpecialTransitionView,
)

urlpatterns = [
    path("", OrderListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", OrderDetailView.as_view(), name="detail"),
    path("<uuid:pk>/cancel/", OrderCancelView.as_view(), name="cancel"),
    path("<uuid:pk>/fulfill/", OrderFulfillView.as_view(), name="fulfill"),
    path("<uuid:pk>/complete/", OrderCompleteView.as_view(), name="complete"),
    path("<uuid:pk>/special-transition/", OrderSpecialTransitionView.as_view(), name="special-transition"),
    path("<uuid:pk>/set-final-price/", OrderFinalPriceView.as_view(), name="set-final-price"),
    path("<uuid:pk>/mark-customer-notified/", OrderCustomerNotifiedView.as_view(), name="mark-customer-notified"),
    path("<uuid:pk>/decline/", OrderDeclineView.as_view(), name="decline"),
    path("<uuid:pk>/receipt/", OrderReceiptView.as_view(), name="receipt"),
]
