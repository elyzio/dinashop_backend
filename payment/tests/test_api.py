import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from inventory.models import InventoryBalance
from order.tests.test_api import make_variant
from people.models import Customer


User = get_user_model()


class PaymentRefundApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="payments@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(name="Buyer", phone="+15551000", address="Address")
        self.variant = make_variant("PAY-SKU", stock=5, price=3000)
        created = self.client.post(
            "/api/order/order/",
            {
                "customer_id": str(self.customer.id),
                "lines": [{"kind": "catalog", "variant_id": str(self.variant.id), "quantity": 1}],
                "delivery_method": "pickup", "pickup_timing": "now", "delivery_address": "",
            },
            format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.order = created.data["order"]

    def test_payment_replay_overpayment_and_refund_restock(self):
        payment_key = uuid.uuid4()
        payload = {
            "order_id": self.order["id"], "order_version": self.order["version"],
            "amount_cents": 3000, "method": "cash", "tendered_cents": 5000,
        }
        payment = self.client.post(
            "/api/payment/payment/record/", payload, format="json",
            HTTP_IDEMPOTENCY_KEY=str(payment_key),
        )
        self.assertEqual(payment.status_code, 201, payment.data)
        self.assertEqual(payment.data["payment"]["change_cents"], 2000)
        replay = self.client.post(
            "/api/payment/payment/record/", payload, format="json",
            HTTP_IDEMPOTENCY_KEY=str(payment_key),
        )
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])

        detail = self.client.get(f"/api/order/order/{self.order['id']}/")
        line_id = detail.data["lines"][0]["id"]
        before = InventoryBalance.objects.get(variant=self.variant).in_hand
        refund = self.client.post(
            "/api/payment/refund/create/",
            {
                "order_id": self.order["id"], "order_version": detail.data["version"],
                "payment_id": payment.data["payment"]["id"],
                "lines": [{"order_line_id": line_id, "quantity": 1, "disposition": "restock"}],
                "method": "cash", "reason": "Returned",
            },
            format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(refund.status_code, 201, refund.data)
        self.assertEqual(refund.data["refund"]["credit_cents"], 3000)
        self.assertEqual(refund.data["refund"]["cash_refund_cents"], 3000)
        self.assertEqual(InventoryBalance.objects.get(variant=self.variant).in_hand, before + 1)

    def test_unauthenticated_payment_is_rejected(self):
        client = APIClient()
        response = client.get("/api/payment/payment/")
        self.assertIn(response.status_code, (401, 403))
