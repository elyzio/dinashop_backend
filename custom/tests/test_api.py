from django.test import TestCase
from rest_framework.test import APIClient

from custom.models import AuditEvent, BusinessSettings, Category, DocumentSequence
from users.models import User


class CustomApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_category_duplicate_cycle_and_protected_delete(self):
        parent = self.client.post(
            "/api/custom/category/", {"name": "Clothing"}, format="json"
        )
        self.assertEqual(parent.status_code, 201)
        parent_id = parent.data["id"]
        duplicate = self.client.post(
            "/api/custom/category/", {"name": " clothing "}, format="json"
        )
        self.assertEqual(duplicate.status_code, 400)
        child = self.client.post(
            "/api/custom/category/",
            {"name": "Shirts", "parent_id": parent_id},
            format="json",
        )
        self.assertEqual(child.status_code, 201)
        cycle = self.client.patch(
            f"/api/custom/category/{parent_id}/",
            {"parent_id": child.data["id"]},
            format="json",
        )
        self.assertEqual(cycle.status_code, 400)
        blocked = self.client.delete(f"/api/custom/category/{parent_id}/")
        self.assertEqual(blocked.status_code, 409)

    def test_business_settings_singleton_and_audit(self):
        response = self.client.put(
            "/api/custom/business-settings/current/",
            {
                "business_name": "Dina Shop",
                "currency": "jpy",
                "timezone": "Asia/Tokyo",
                "low_stock_threshold": 4,
                "whatsapp_phone": "+81 (90) 1234-5678",
            },
            format="json",
        )
        self.assertIn(response.status_code, (200, 201))
        self.assertEqual(response.data["currency"], "JPY")
        self.assertEqual(response.data["whatsapp_phone"], "+819012345678")
        self.assertEqual(BusinessSettings.objects.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="business_settings.updated").exists())

    def test_audit_events_are_read_only_and_sequences_are_internal(self):
        AuditEvent.objects.create(
            actor=self.user,
            action="test.event",
            entity_type="test.Entity",
            entity_id="1",
        )
        listing = self.client.get("/api/custom/audit-event/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(self.client.post("/api/custom/audit-event/", {}, format="json").status_code, 405)
        self.assertEqual(self.client.get("/api/custom/document-sequence/").status_code, 404)
        self.assertEqual(
            set(DocumentSequence.objects.values_list("key", flat=True)),
            {"order", "special_order", "payment", "refund"},
        )
