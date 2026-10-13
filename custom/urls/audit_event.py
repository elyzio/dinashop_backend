from django.urls import path

from custom.views.audit_event import AuditEventDetailView, AuditEventListView

app_name = "audit_event"

urlpatterns = [
    path("", AuditEventListView.as_view(), name="list"),
    path("<uuid:pk>/", AuditEventDetailView.as_view(), name="detail"),
]
