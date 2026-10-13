from django.urls import include, path

app_name = "users"

urlpatterns = [
    path("user/", include("users.urls.user")),
    path("notification-receipt/", include("users.urls.notification_receipt")),
]
