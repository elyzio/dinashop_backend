from django.urls import path
from inventory.views.stock_reservation import StockReservationDetailView, StockReservationListView
app_name = "stock_reservation"
urlpatterns = [path("", StockReservationListView.as_view(), name="list"), path("<uuid:pk>/", StockReservationDetailView.as_view(), name="detail")]
