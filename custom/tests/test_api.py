from django.core.exceptions import ValidationError
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
                "email": "contact@example.com",
                "latitude": "-8.556856",
                "longitude": "125.560314",
            },
            format="json",
        )
        self.assertIn(response.status_code, (200, 201))
        self.assertEqual(response.data["currency"], "JPY")
        self.assertEqual(response.data["whatsapp_phone"], "+819012345678")
        self.assertEqual(response.data["email"], "contact@example.com")
        self.assertEqual(response.data["latitude"], "-8.556856")
        self.assertEqual(response.data["longitude"], "125.560314")
        self.assertEqual(BusinessSettings.objects.count(), 1)
        self.assertTrue(AuditEvent.objects.filter(action="business_settings.updated").exists())

    def test_business_contact_coordinates_are_optional_paired_and_bounded(self):
        endpoint = "/api/custom/business-settings/current/"
        self.assertEqual(
            self.client.patch(endpoint, {"email": "invalid"}, format="json").status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                endpoint,
                {"latitude": "91.000000", "longitude": "125.560314"},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.patch(
                endpoint,
                {"latitude": "-8.556856"},
                format="json",
            ).status_code,
            400,
        )

        saved = self.client.patch(
            endpoint,
            {
                "email": " public@example.com ",
                "latitude": "-8.556856",
                "longitude": "125.560314",
            },
            format="json",
        )
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(saved.data["email"], "public@example.com")

        incomplete_clear = self.client.patch(
            endpoint, {"latitude": None}, format="json"
        )
        self.assertEqual(incomplete_clear.status_code, 400)
        cleared = self.client.patch(
            endpoint, {"latitude": None, "longitude": None}, format="json"
        )
        self.assertEqual(cleared.status_code, 200, cleared.data)
        self.assertIsNone(cleared.data["latitude"])
        self.assertIsNone(cleared.data["longitude"])

    def test_business_settings_model_requires_coordinate_pair(self):
        settings = BusinessSettings.objects.get(key="default")
        settings.latitude = "-8.556856"
        settings.longitude = None
        with self.assertRaises(ValidationError):
            settings.full_clean()

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
