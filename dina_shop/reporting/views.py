from django.http import Http404, HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from dina_shop.reporting.serializers import (
    DashboardResponseSerializer,
    DateRangeQuerySerializer,
    ReportResponseSerializer,
)
from dina_shop.reporting.services import build_dashboard, build_report, report_csv, report_ids


DATE_PARAMETERS = [
    OpenApiParameter("from", str, description="Inclusive start date in YYYY-MM-DD format."),
    OpenApiParameter("to", str, description="Inclusive end date in YYYY-MM-DD format."),
]


class DashboardSummaryView(GenericAPIView):
    serializer_class = DashboardResponseSerializer

    @extend_schema(responses=DashboardResponseSerializer)
    def get(self, request):
        serializer = self.get_serializer(build_dashboard())
        return Response(serializer.data)


class ReportView(GenericAPIView):
    serializer_class = ReportResponseSerializer

    def _report(self, request, report_id):
        if report_id not in report_ids():
            raise Http404("Unknown report.")
        query = DateRangeQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return build_report(report_id, query.validated_data["from"], query.validated_data["to"])

    @extend_schema(parameters=DATE_PARAMETERS, responses=ReportResponseSerializer)
    def get(self, request, report_id):
        serializer = self.get_serializer(self._report(request, report_id))
        return Response(serializer.data)


class ReportCsvView(ReportView):
    @extend_schema(parameters=DATE_PARAMETERS, responses={(200, "text/csv"): bytes})
    def get(self, request, report_id):
        report = self._report(request, report_id)
        response = HttpResponse(report_csv(report), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{report_id}-{report["from"]}-{report["to"]}.csv"'
        )
        return response
