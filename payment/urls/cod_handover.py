from django.urls import path

from payment.views.cod_handover import (
    CodHandoverDetailView, CodHandoverListView, CodHandoverRecordView,
    CodHandoverSummaryView,
)

urlpatterns = [
    path("", CodHandoverListView.as_view(), name="list"),
    path("record/", CodHandoverRecordView.as_view(), name="record"),
    path("summary/", CodHandoverSummaryView.as_view(), name="summary"),
    path("<uuid:pk>/", CodHandoverDetailView.as_view(), name="detail"),
]
