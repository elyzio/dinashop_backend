import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Product, ProductCategory, ProductVariant
from custom.models import Category
from inventory.models import InventoryBalance, StockReservation
from people.models import Customer


User = get_user_model()


def make_variant(sku="SKU-1", stock=10, price=2500):
    category = Category.objects.create(name=f"Category {sku}", slug=f"category-{sku.lower()}")
    product = Product.objects.create(name=f"Product {sku}")
    ProductCategory.objects.create(product=product, category=category, is_primary=True)
    variant = ProductVariant.objects.create(product=product, sku=sku, selling_price_cents=price)
    InventoryBalance.objects.create(variant=variant, in_hand=stock)
    return variant


class OrderApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="orders@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.customer = Customer.objects.create(name="Named", phone="+15550001", address="Address")
        self.variant = make_variant()

    def post_order(self, payload, key=None):
        return self.client.post(
            "/api/order/order/", payload, format="json",
            HTTP_IDEMPOTENCY_KEY=str(key or uuid.uuid4()),
        )

    def test_order_create_replay_reservation_and_fulfilment(self):
        key = uuid.uuid4()
        payload = {
            "customer_id": str(self.customer.id),
            "lines": [{"kind": "catalog", "variant_id": str(self.variant.id), "quantity": 2}],
            "delivery_method": "pickup", "pickup_timing": "later", "delivery_address": "",
        }
        created = self.post_order(payload, key)
        self.assertEqual(created.status_code, 201, created.data)
        replay = self.post_order(payload, key)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        reservation = StockReservation.objects.get(order_line__order_id=created.data["order"]["id"])
        self.assertEqual(reservation.quantity, 2)
        fulfilled = self.client.post(
            f"/api/order/order/{created.data['order']['id']}/fulfill/",
            {"version": created.data["order"]["version"]}, format="json",
        )
        self.assertEqual(fulfilled.status_code, 200, fulfilled.data)
        self.variant.inventory.refresh_from_db()
        self.assertEqual(self.variant.inventory.in_hand, 8)
        self.assertEqual(self.variant.inventory.promised, 0)

    def test_special_line_receiving_generates_hidden_reserved_variant(self):
        key = uuid.uuid4()
        payload = {
            "customer_id": str(self.customer.id),
            "lines": [{
                "kind": "special", "description": "Imported lamp",
                "quantity": 1, "unit_price_cents": 12000,
            }],
            "delivery_method": "pickup", "pickup_timing": "later", "delivery_address": "",
            "customer_accepted_price_change": True,
        }
        created = self.post_order(payload, key)
        order = created.data["order"]
        for target in ("quoted", "confirmed"):
            transitioned = self.client.post(
                f"/api/order/order/{order['id']}/special-transition/",
                {"version": order["version"], "target": target}, format="json",
            )
            self.assertEqual(transitioned.status_code, 200, transitioned.data)
            order = transitioned.data
        line_id = order["lines"][0]["id"]
        received = self.client.post(
            f"/api/order/order-line/{line_id}/receive/",
            {"total_product_cost_cents": 7000, "tax_cents": 500, "fees_cents": 200},
            format="json", HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()),
        )
        self.assertEqual(received.status_code, 201, received.data)
        line = received.data["order_line"]
        self.assertIsNotNone(line["variant"])
        variant = ProductVariant.objects.get(pk=line["variant"])
        self.assertEqual(variant.product.visibility, "hidden")
        self.assertEqual(variant.inventory.in_hand, 1)
        self.assertEqual(variant.inventory.promised, 1)
        replay = self.post_order(payload, key)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])

    def test_initial_payment_is_atomic_and_checked_on_replay(self):
        key = uuid.uuid4()
        payload = {
            "customer_id": str(self.customer.id),
            "lines": [{"kind": "catalog", "variant_id": str(self.variant.id), "quantity": 1}],
            "delivery_method": "pickup", "pickup_timing": "later", "delivery_address": "",
            "initial_payment": {
                "amount_cents": 1000, "method": "cash", "tendered_cents": 1200,
            },
        }
        created = self.post_order(payload, key)
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["order"]["paid_cents"], 1000)

        replay = self.post_order(payload, key)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])

        changed = {**payload, "initial_payment": {**payload["initial_payment"], "amount_cents": 900}}
        conflict = self.post_order(changed, key)
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.assertEqual(conflict.data["error"]["code"], "idempotency_conflict")
