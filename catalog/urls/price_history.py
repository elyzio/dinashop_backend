from django.urls import path
from catalog.views.price_history import PriceHistoryDetailView, PriceHistoryListView
app_name = "price_history"
urlpatterns = [path("", PriceHistoryListView.as_view(), name="list"), path("<uuid:pk>/", PriceHistoryDetailView.as_view(), name="detail")]
