from django.urls import include, path

app_name = "inventory"

urlpatterns = [
    path("inventory-balance/", include("inventory.urls.inventory_balance")),
    path("stock-reservation/", include("inventory.urls.stock_reservation")),
    path("stock-movement/", include("inventory.urls.stock_movement")),
]
