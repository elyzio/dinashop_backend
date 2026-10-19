from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from order.models import Order, OrderLine
from people.models import Customer


User = get_user_model()


class ReportingApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reports@example.com",
            password="safe-pass",
        )
        self.customer = Customer.objects.create(
            name="Report Customer",
            phone="+15550001",
            address="Address",
        )
        self.order = Order.objects.create(
            number="ORD-REPORT-1",
            customer=self.customer,
            created_by=self.user,
            delivery_method=Order.DeliveryMethod.PICKUP,
            pickup_timing=Order.PickupTiming.LATER,
            customer_name=self.customer.name,
            customer_phone=self.customer.phone,
        )
        OrderLine.objects.create(
            order=self.order,
            kind=OrderLine.Kind.SPECIAL,
            description="Report item",
            quantity=2,
            unit_price_cents=1250,
            estimated_tax_cents=200,
        )
        self.client = APIClient()

    def _range(self):
        today = timezone.localdate().isoformat()
        return {"from": today, "to": today}

    def test_reporting_endpoints_require_authentication(self):
        self.assertEqual(self.client.get("/api/dashboard/summary/").status_code, 401)
        self.assertEqual(
            self.client.get("/api/report/sales/", self._range()).status_code,
            401,
        )
        self.assertEqual(
            self.client.get("/api/report/sales/csv/", self._range()).status_code,
            401,
        )

    def test_sales_report_and_csv_use_server_values(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/report/sales/", self._range())

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["rows"][0]["order_number"], self.order.number)
        self.assertEqual(response.data["rows"][0]["total_cents"], 2700)

        csv_response = self.client.get("/api/report/sales/csv/", self._range())
        self.assertEqual(csv_response.status_code, 200)
        self.assertEqual(csv_response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("27.00", csv_response.content.decode("utf-8"))

    def test_dashboard_returns_metrics_and_six_month_series(self):
        self.client.force_authenticate(self.user)
        response = self.client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["metrics"]["active_orders"], 1)
        self.assertEqual(response.data["metrics"]["balance_due_cents"], 2700)
        self.assertEqual(len(response.data["monthly_profit"]), 6)

    def test_reversed_range_returns_standard_validation_error(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            "/api/report/sales/",
            {"from": "2026-10-31", "to": "2026-10-01"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("from", response.data["error"]["fields"])
