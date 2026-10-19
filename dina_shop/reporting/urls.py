from django.urls import path

from dina_shop.reporting.views import DashboardSummaryView, ReportCsvView, ReportView


urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("report/<slug:report_id>/", ReportView.as_view(), name="report"),
    path("report/<slug:report_id>/csv/", ReportCsvView.as_view(), name="report-csv"),
]
