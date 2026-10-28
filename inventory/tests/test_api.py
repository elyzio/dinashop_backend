import uuid

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Product, ProductVariant
from inventory.models import InventoryBalance, StockMovement
from users.models import User


class InventoryApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="stock@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.product = Product.objects.create(name="Stock item")
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="STOCK-1",
            selling_price_cents=1000,
        )
        self.balance = InventoryBalance.objects.create(variant=self.variant)

    def test_receipt_is_idempotent_and_uses_half_up_integer_cost(self):
        key = str(uuid.uuid4())
        payload = {
            "variant_id": str(self.variant.id),
            "quantity": 3,
            "price_paid_cents": 1000,
            "tax_cents": 1,
            "fees_cents": 0,
        }
        first = self.client.post(
            "/api/inventory/stock-movement/receive/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        replay = self.client.post(
            "/api/inventory/stock-movement/receive/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.in_hand, 3)
        self.assertEqual(self.balance.last_landed_cost_cents, 334)
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_adjustment_cannot_reduce_stock_below_promised(self):
        self.balance.in_hand = 4
        self.balance.promised = 3
        self.balance.save()
        response = self.client.post(
            "/api/inventory/stock-movement/adjust/",
            {
                "variant_id": str(self.variant.id),
                "quantity_delta": -2,
                "reason": "count_correction",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.balance.refresh_from_db()
        self.assertEqual(self.balance.in_hand, 4)

    def test_history_endpoints_are_read_only(self):
        listing = self.client.get("/api/inventory/inventory-balance/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(
            self.client.post("/api/inventory/stock-movement/", {}, format="json").status_code,
            405,
        )

    def test_receipt_requires_uuid_idempotency_key(self):
        payload = {
            "variant_id": str(self.variant.id),
            "quantity": 1,
            "price_paid_cents": 100,
        }
        missing = self.client.post(
            "/api/inventory/stock-movement/receive/", payload, format="json"
        )
        invalid = self.client.post(
            "/api/inventory/stock-movement/receive/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY="not-a-uuid",
        )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_stock_history_filters_one_variant_type_and_date_range(self):
        other_variant = ProductVariant.objects.create(
            product=self.product,
            sku="STOCK-2",
            selling_price_cents=1200,
        )
        InventoryBalance.objects.create(variant=other_variant)
        StockMovement.objects.create(
            variant=self.variant,
            movement_type=StockMovement.Type.RECEIVED,
            quantity_delta=3,
            reference="Receipt one",
            recorded_by=self.user,
        )
        StockMovement.objects.create(
            variant=self.variant,
            movement_type=StockMovement.Type.ADJUSTMENT,
            quantity_delta=1,
            reference="Adjustment one",
            recorded_by=self.user,
        )
        StockMovement.objects.create(
            variant=other_variant,
            movement_type=StockMovement.Type.RECEIVED,
            quantity_delta=2,
            reference="Other receipt",
            recorded_by=self.user,
        )
        today = timezone.localdate().isoformat()

        response = self.client.get(
            "/api/inventory/stock-movement/",
            {
                "variant": str(self.variant.id),
                "movement_type": "received",
                "from": today,
                "to": today,
                "page_size": 25,
            },
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["reference"], "Receipt one")
        self.assertEqual(
            str(response.data["results"][0]["variant"]), str(self.variant.id)
        )
