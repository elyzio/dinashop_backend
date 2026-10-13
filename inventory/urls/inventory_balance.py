from django.urls import path
from inventory.views.inventory_balance import InventoryBalanceDetailView, InventoryBalanceListView
app_name = "inventory_balance"
urlpatterns = [path("", InventoryBalanceListView.as_view(), name="list"), path("<uuid:pk>/", InventoryBalanceDetailView.as_view(), name="detail")]
