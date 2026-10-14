from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from people.models import Customer


User = get_user_model()


class PeopleApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="owner@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_customer_duplicate_warning_and_walk_in_protection(self):
        first = self.client.post(
            "/api/people/customer/",
            {"name": "Alice", "phone": "+1 (555) 0100", "address": "One Street"},
            format="json",
        )
        self.assertEqual(first.status_code, 201, first.data)
        second = self.client.post(
            "/api/people/customer/",
            {"name": "Alice Two", "phone": "+1-555-0100", "address": "Two Street"},
            format="json",
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(second.data["duplicate_phone_warning"]["customer_id"], first.data["id"])
        walk_in = Customer.objects.get(is_walk_in=True)
        blocked = self.client.patch(
            f"/api/people/customer/{walk_in.id}/", {"name": "Changed"}, format="json"
        )
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.data["error"]["code"], "walk_in_protected")

    def test_helper_create_deactivate_and_reactivate(self):
        created = self.client.post(
            "/api/people/helper/", {"name": "Courier", "phone": "555-1234"}, format="json"
        )
        self.assertEqual(created.status_code, 201, created.data)
        helper_id = created.data["id"]
        inactive = self.client.post(f"/api/people/helper/{helper_id}/deactivate/", {}, format="json")
        self.assertFalse(inactive.data["is_active"])
        active = self.client.post(f"/api/people/helper/{helper_id}/reactivate/", {}, format="json")
        self.assertTrue(active.data["is_active"])
