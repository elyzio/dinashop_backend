from django.urls import path
from inventory.views.stock_movement import StockAdjustmentView, StockMovementDetailView, StockMovementListView, StockReceiptView
app_name = "stock_movement"
urlpatterns = [path("", StockMovementListView.as_view(), name="list"), path("receive/", StockReceiptView.as_view(), name="receive"), path("adjust/", StockAdjustmentView.as_view(), name="adjust"), path("<uuid:pk>/", StockMovementDetailView.as_view(), name="detail")]
