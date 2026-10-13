from django.urls import path

from custom.views.category import CategoryDetailView, CategoryListCreateView

app_name = "category"

urlpatterns = [
    path("", CategoryListCreateView.as_view(), name="list-create"),
    path("<uuid:pk>/", CategoryDetailView.as_view(), name="detail"),
]
