from django.urls import path

from custom.views.business_settings import BusinessSettingsCurrentView

app_name = "business_settings"

urlpatterns = [path("current/", BusinessSettingsCurrentView.as_view(), name="current")]
