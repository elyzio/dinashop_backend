from django.urls import path

from storefront.views.category import PublicCategoryListView

app_name = "category"
urlpatterns = [path("", PublicCategoryListView.as_view(), name="list")]
