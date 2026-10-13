from django.urls import include, path

app_name = "custom"

urlpatterns = [
    path("category/", include("custom.urls.category")),
    path("business-settings/", include("custom.urls.business_settings")),
    path("audit-event/", include("custom.urls.audit_event")),
]
