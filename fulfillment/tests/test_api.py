import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from order.tests.test_api import make_variant
from payment.models import CodHandover, Payment
from people.models import Customer, Helper


User = get_user_model()


class DeliveryCodApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="delivery@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(name="Delivery Buyer", phone="+15552000", address="Road")
        self.helper = Helper.objects.create(name="Courier", phone="+15553000")
        self.variant = make_variant("COD-SKU", stock=4, price=4500)

    def create_delivery_order(self):
        response = self.client.post(
            "/api/order/order/",
            {
                "customer_id": str(self.customer.id),
                "lines": [{"kind": "catalog", "variant_id": str(self.variant.id), "quantity": 1}],
                "delivery_method": "delivery", "delivery_address": "Road", "cod": True,
            },
            format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["order"]

    def test_delivery_creates_cod_payment_and_partial_handover(self):
        order = self.create_delivery_order()
        created = self.client.post(
            "/api/fulfillment/delivery-job/",
            {
                "order_id": order["id"], "helper_id": str(self.helper.id),
                "fee_cents": 500, "fuel_cents": 100, "order_version": order["version"],
            }, format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        job = created.data
        order_version = self.client.get(f"/api/order/order/{order['id']}/").data["version"]
        started = self.client.post(
            f"/api/fulfillment/delivery-job/{job['id']}/start/",
            {"order_version": order_version}, format="json",
        )
        self.assertEqual(started.status_code, 200, started.data)
        order_version = self.client.get(f"/api/order/order/{order['id']}/").data["version"]
        delivered = self.client.post(
            f"/api/fulfillment/delivery-job/{job['id']}/deliver/",
            {"order_version": order_version}, format="json",
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(delivered.status_code, 200, delivered.data)
        payment = Payment.objects.get(order_id=order["id"])
        self.assertEqual(payment.amount_cents, 4500)

        handover = self.client.post(
            "/api/payment/cod-handover/record/",
            {"helper_id": str(self.helper.id), "order_id": order["id"], "amount_cents": 2000},
            format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(handover.status_code, 201, handover.data)
        self.assertEqual(CodHandover.objects.get().amount_cents, 2000)
        summary = self.client.get("/api/payment/cod-handover/summary/")
        self.assertEqual(summary.data["held_cents"], 2500)

    def test_failed_delivery_cancels_order_and_releases_stock(self):
        order = self.create_delivery_order()
        job = self.client.post(
            "/api/fulfillment/delivery-job/",
            {"order_id": order["id"], "helper_id": str(self.helper.id), "order_version": order["version"]},
            format="json",
        ).data
        version = self.client.get(f"/api/order/order/{order['id']}/").data["version"]
        self.client.post(
            f"/api/fulfillment/delivery-job/{job['id']}/start/",
            {"order_version": version}, format="json",
        )
        version = self.client.get(f"/api/order/order/{order['id']}/").data["version"]
        failed = self.client.post(
            f"/api/fulfillment/delivery-job/{job['id']}/fail/",
            {"order_version": version, "failure_reason": "Customer unavailable"}, format="json",
        )
        self.assertEqual(failed.status_code, 200, failed.data)
        order_detail = self.client.get(f"/api/order/order/{order['id']}/")
        self.assertEqual(order_detail.data["status"], "cancelled")
        self.variant.inventory.refresh_from_db()
        self.assertEqual(self.variant.inventory.promised, 0)
