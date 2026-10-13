from django.urls import path

from users.views.notification_receipt import (
    NotificationAcknowledgeView,
    NotificationReadAllView,
    NotificationReceiptListView,
)

app_name = "notification_receipt"

urlpatterns = [
    path("", NotificationReceiptListView.as_view(), name="list"),
    path("acknowledge/", NotificationAcknowledgeView.as_view(), name="acknowledge"),
    path("read-all/", NotificationReadAllView.as_view(), name="read-all"),
]
