import io
import tempfile
import uuid

from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from catalog.models import PriceHistory, Product, ProductImage, ProductVariant
from custom.models import AuditEvent, Category
from inventory.models import InventoryBalance
from users.models import User


def product_payload(category, *, sku="SHIRT-BLACK"):
    return {
        "name": "Classic T-Shirt",
        "description": "Soft cotton shirt.",
        "brand": "Dina",
        "visibility": "active",
        "category_ids": [str(category.id)],
        "primary_category_id": str(category.id),
        "option_definitions": [{"name": "Color", "values": ["Black", "White"]}],
        "variants": [
            {
                "sku": sku,
                "options": {"Color": "Black"},
                "selling_price_cents": 2500,
                "is_active": True,
            }
        ],
    }


class CatalogApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="catalog@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.category = Category.objects.create(name="Clothing", slug="clothing")

    def create_product(self):
        response = self.client.post(
            "/api/catalog/product/", product_payload(self.category), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_product_aggregate_is_created_atomically_with_inventory(self):
        response = self.create_product()
        product = Product.objects.get(pk=response.data["id"])
        variant = product.variants.get()
        self.assertEqual(variant.sku, "SHIRT-BLACK")
        self.assertTrue(InventoryBalance.objects.filter(variant=variant).exists())
        self.assertEqual(response.data["primary_category_id"], str(self.category.id))
        self.assertFalse(PriceHistory.objects.filter(variant=variant).exists())

    def test_single_product_has_one_internal_variant_without_options(self):
        payload = product_payload(self.category, sku="SINGLE-1")
        payload["option_definitions"] = []
        payload["variants"][0]["options"] = {}
        response = self.client.post("/api/catalog/product/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertFalse(product.has_variants)
        self.assertEqual(product.options.count(), 0)
        self.assertEqual(product.variants.count(), 1)

    def test_invalid_primary_category_rolls_back(self):
        payload = product_payload(self.category)
        payload["primary_category_id"] = str(uuid.uuid4())
        response = self.client.post("/api/catalog/product/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Product.objects.count(), 0)

    def test_duplicate_sku_is_rejected_without_partial_product(self):
        self.create_product()
        response = self.client.post(
            "/api/catalog/product/",
            product_payload(self.category, sku=" shirt-black "),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Product.objects.count(), 1)

    def test_optional_manual_barcode_is_trimmed_preserved_and_unique(self):
        payload = product_payload(self.category)
        payload["variants"][0]["barcode"] = " 0012345678905 "
        created = self.client.post("/api/catalog/product/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        variant = ProductVariant.objects.get(pk=created.data["variants"][0]["id"])
        self.assertEqual(variant.barcode, "0012345678905")
        self.assertEqual(created.data["variants"][0]["barcode"], "0012345678905")
        self.assertTrue(
            AuditEvent.objects.filter(
                action="product_variant.barcode_updated",
                entity_id=str(variant.id),
            ).exists()
        )

        duplicate = product_payload(self.category, sku="SHIRT-WHITE")
        duplicate["variants"][0]["barcode"] = "0012345678905"
        rejected = self.client.post("/api/catalog/product/", duplicate, format="json")
        self.assertEqual(rejected.status_code, 400, rejected.data)

        blank = product_payload(self.category, sku="SHIRT-BLANK")
        blank["variants"][0]["barcode"] = "   "
        accepted = self.client.post("/api/catalog/product/", blank, format="json")
        self.assertEqual(accepted.status_code, 201, accepted.data)
        self.assertIsNone(accepted.data["variants"][0]["barcode"])

    def test_barcode_rejects_control_characters_and_values_over_100_characters(self):
        control = product_payload(self.category)
        control["variants"][0]["barcode"] = "ABC\t123"
        self.assertEqual(
            self.client.post("/api/catalog/product/", control, format="json").status_code,
            400,
        )
        too_long = product_payload(self.category)
        too_long["variants"][0]["barcode"] = "A" * 101
        self.assertEqual(
            self.client.post("/api/catalog/product/", too_long, format="json").status_code,
            400,
        )

    def test_generated_barcode_uses_sequence_and_cannot_overwrite_existing_value(self):
        payload = product_payload(self.category)
        payload["variants"][0]["generate_barcode"] = True
        created = self.client.post("/api/catalog/product/", payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        variant_id = created.data["variants"][0]["id"]
        self.assertEqual(created.data["variants"][0]["barcode"], "DS-000000000001")
        self.assertTrue(
            AuditEvent.objects.filter(
                action="product_variant.barcode_generated",
                entity_id=variant_id,
            ).exists()
        )
        second_payload = product_payload(self.category, sku="SHIRT-WHITE")
        second_payload["variants"][0]["generate_barcode"] = True
        second = self.client.post(
            "/api/catalog/product/", second_payload, format="json"
        )
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(
            second.data["variants"][0]["barcode"], "DS-000000000002"
        )
        self.assertNotEqual(
            created.data["variants"][0]["barcode"],
            second.data["variants"][0]["barcode"],
        )
        conflict = self.client.post(
            f"/api/catalog/product-variant/{variant_id}/barcode/generate/",
            format="json",
        )
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.assertEqual(conflict.data["error"]["code"], "barcode_exists")

    def test_variant_grid_preserves_omitted_barcode_and_can_clear_it(self):
        payload = product_payload(self.category)
        payload["variants"][0]["barcode"] = "Case-Sensitive-001"
        created = self.client.post("/api/catalog/product/", payload, format="json")
        product_id = created.data["id"]
        variant = created.data["variants"][0]
        grid = {
            "option_definitions": [{"name": "Color", "values": ["Black"]}],
            "variants": [
                {
                    "id": variant["id"],
                    "sku": variant["sku"],
                    "options": {"Color": "Black"},
                    "selling_price_cents": 2500,
                    "is_active": True,
                }
            ],
        }
        preserved = self.client.put(
            f"/api/catalog/product/{product_id}/variant-grid/", grid, format="json"
        )
        self.assertEqual(preserved.status_code, 200, preserved.data)
        self.assertEqual(preserved.data["variants"][0]["barcode"], "Case-Sensitive-001")
        grid["variants"][0]["barcode"] = None
        cleared = self.client.put(
            f"/api/catalog/product/{product_id}/variant-grid/", grid, format="json"
        )
        self.assertEqual(cleared.status_code, 200, cleared.data)
        self.assertIsNone(cleared.data["variants"][0]["barcode"])

    def test_barcode_lookup_requires_authentication_and_enforces_sellability(self):
        payload = product_payload(self.category)
        payload["variants"][0]["barcode"] = "012345678905"
        created = self.client.post("/api/catalog/product/", payload, format="json")
        product = Product.objects.get(pk=created.data["id"])
        variant = product.variants.get()
        variant.inventory.in_hand = 2
        variant.inventory.save(update_fields=["in_hand"])

        anonymous = APIClient().get(
            "/api/catalog/product-variant/barcode-lookup/",
            {"barcode": variant.barcode},
        )
        self.assertEqual(anonymous.status_code, 401, anonymous.data)
        found = self.client.get(
            "/api/catalog/product-variant/barcode-lookup/",
            {"barcode": variant.barcode},
        )
        self.assertEqual(found.status_code, 200, found.data)
        self.assertEqual(found.data["id"], str(variant.id))
        self.assertEqual(found.data["product_name"], "Classic T-Shirt")
        self.assertEqual(found.data["available"], 2)

        missing = self.client.get(
            "/api/catalog/product-variant/barcode-lookup/",
            {"barcode": "UNKNOWN"},
        )
        self.assertEqual(missing.status_code, 404, missing.data)
        self.assertEqual(missing.data["error"]["code"], "barcode_not_found")

        variant.inventory.in_hand = 0
        variant.inventory.save(update_fields=["in_hand"])
        sold_out = self.client.get(
            "/api/catalog/product-variant/barcode-lookup/",
            {"barcode": variant.barcode},
        )
        self.assertEqual(sold_out.status_code, 409, sold_out.data)
        self.assertEqual(sold_out.data["error"]["code"], "sold_out")

        variant.inventory.in_hand = 2
        variant.inventory.save(update_fields=["in_hand"])
        product.visibility = Product.Visibility.HIDDEN
        product.save(update_fields=["visibility"])
        unavailable = self.client.get(
            "/api/catalog/product-variant/barcode-lookup/",
            {"barcode": variant.barcode},
        )
        self.assertEqual(unavailable.status_code, 409, unavailable.data)
        self.assertEqual(unavailable.data["error"]["code"], "variant_not_sellable")

    def test_pricing_appends_history_and_visibility_checks_promised_stock(self):
        created = self.create_product()
        variant_id = created.data["variants"][0]["id"]
        priced = self.client.patch(
            f"/api/catalog/product-variant/{variant_id}/pricing/",
            {"selling_price_cents": 2750},
            format="json",
        )
        self.assertEqual(priced.status_code, 200, priced.data)
        self.assertEqual(PriceHistory.objects.filter(variant_id=variant_id).count(), 1)
        balance = InventoryBalance.objects.get(variant_id=variant_id)
        balance.in_hand = 2
        balance.promised = 1
        balance.save()
        blocked = self.client.post(
            f"/api/catalog/product/{created.data['id']}/visibility/",
            {"visibility": "hidden"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 409)

    def test_price_history_filters_one_variant_kind_and_date_range(self):
        created = self.create_product()
        variant = ProductVariant.objects.get(pk=created.data["variants"][0]["id"])
        PriceHistory.objects.create(
            variant=variant,
            kind=PriceHistory.Kind.STANDARD,
            previous_cents=2000,
            new_cents=2500,
            changed_by=self.user,
        )
        PriceHistory.objects.create(
            variant=variant,
            kind=PriceHistory.Kind.SALE,
            previous_cents=None,
            new_cents=2200,
            changed_by=self.user,
        )
        today = timezone.localdate().isoformat()

        response = self.client.get(
            "/api/catalog/price-history/",
            {
                "variant": str(variant.id),
                "kind": "standard",
                "from": today,
                "to": today,
                "page_size": 25,
            },
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["kind"], "standard")
        self.assertEqual(
            str(response.data["results"][0]["variant"]), str(variant.id)
        )

    def test_mode_conversion_is_allowed_before_operational_history(self):
        payload = product_payload(self.category, sku="MODE-1")
        payload["option_definitions"] = []
        payload["variants"][0]["options"] = {}
        created = self.client.post("/api/catalog/product/", payload, format="json")
        variant_id = created.data["variants"][0]["id"]
        converted = self.client.put(
            f"/api/catalog/product/{created.data['id']}/variant-grid/",
            {
                "option_definitions": [{"name": "Color", "values": ["Black"]}],
                "variants": [
                    {
                        "id": variant_id,
                        "sku": "MODE-1",
                        "options": {"Color": "Black"},
                        "selling_price_cents": 2500,
                        "is_active": True,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(converted.status_code, 200, converted.data)
        self.assertTrue(Product.objects.get(pk=created.data["id"]).has_variants)

    def test_mode_conversion_is_locked_after_price_history(self):
        created = self.create_product()
        variant = ProductVariant.objects.get(pk=created.data["variants"][0]["id"])
        PriceHistory.objects.create(
            variant=variant,
            kind=PriceHistory.Kind.STANDARD,
            previous_cents=2000,
            new_cents=2500,
            changed_by=self.user,
        )
        blocked = self.client.put(
            f"/api/catalog/product/{created.data['id']}/variant-grid/",
            {
                "option_definitions": [],
                "variants": [
                    {
                        "id": str(variant.id),
                        "sku": variant.sku,
                        "options": {},
                        "selling_price_cents": variant.selling_price_cents,
                        "is_active": True,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(blocked.status_code, 409, blocked.data)
        self.assertEqual(blocked.data["error"]["code"], "variant_mode_locked")

    def test_detail_update_does_not_change_variant_pricing_or_history(self):
        created = self.create_product()
        variant = ProductVariant.objects.get(pk=created.data["variants"][0]["id"])
        response = self.client.patch(
            f"/api/catalog/product/{created.data['id']}/",
            {"name": "Renamed shirt", "brand": "Updated brand"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        variant.refresh_from_db()
        self.assertEqual(variant.selling_price_cents, 2500)
        self.assertFalse(PriceHistory.objects.filter(variant=variant).exists())

    def test_list_uses_paginated_card_payload_and_detail_stays_complete(self):
        created = self.create_product()
        listed = self.client.get("/api/catalog/product/?page_size=50")
        self.assertEqual(listed.status_code, 200, listed.data)
        card = listed.data["results"][0]
        self.assertEqual(card["id"], created.data["id"])
        self.assertIn("display_price_cents", card)
        self.assertIn("available_quantity", card)
        self.assertNotIn("variants", card)
        detail = self.client.get(f"/api/catalog/product/{created.data['id']}/")
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertIn("variants", detail.data)


class ProductImageApiTests(TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.override = override_settings(
            STORAGES={
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.tempdir.name, "base_url": "/media/"},
                },
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
                },
            }
        )
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(self.tempdir.cleanup)
        self.user = User.objects.create_user(email="images@example.com", password="safe-pass")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        category = Category.objects.create(name="Images", slug="images")
        response = self.client.post(
            "/api/catalog/product/", product_payload(category, sku="IMAGE-1"), format="json"
        )
        self.product_id = response.data["id"]

    @staticmethod
    def image_file(size=(2000, 1000)):
        stream = io.BytesIO()
        Image.new("RGB", size, "red").save(stream, format="JPEG")
        stream.seek(0)
        stream.name = "source.jpg"
        return stream

    def test_upload_converts_to_bounded_webp_and_reorder_requires_complete_set(self):
        uploaded = self.client.post(
            "/api/catalog/product-image/",
            {"product_id": self.product_id, "image": self.image_file(), "alt_text": "Front"},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, 201, uploaded.data)
        image = ProductImage.objects.get(pk=uploaded.data["id"])
        self.assertTrue(image.image.name.endswith(".webp"))
        self.assertLessEqual(image.width, 1600)
        self.assertLessEqual(image.height, 1600)
        self.assertEqual(image.renditions.count(), 3)
        self.assertEqual(
            {item["kind"] for item in uploaded.data["renditions"]},
            {"thumbnail", "card", "detail"},
        )
        incomplete = self.client.post(
            "/api/catalog/product-image/reorder/",
            {"product_id": self.product_id, "image_ids": []},
            format="json",
        )
        self.assertEqual(incomplete.status_code, 400)

    def test_invalid_oversized_and_ninth_images_are_rejected(self):
        spoofed = SimpleUploadedFile("fake.jpg", b"not-an-image", content_type="image/jpeg")
        invalid = self.client.post(
            "/api/catalog/product-image/",
            {"product_id": self.product_id, "image": spoofed},
            format="multipart",
        )
        self.assertEqual(invalid.status_code, 400)

        oversized_stream = io.BytesIO()
        Image.new("RGB", (1400, 1400), "blue").save(oversized_stream, format="BMP")
        oversized = SimpleUploadedFile(
            "large.bmp",
            oversized_stream.getvalue(),
            content_type="image/bmp",
        )
        too_large = self.client.post(
            "/api/catalog/product-image/",
            {"product_id": self.product_id, "image": oversized},
            format="multipart",
        )
        self.assertEqual(too_large.status_code, 413)

        for _ in range(8):
            accepted = self.client.post(
                "/api/catalog/product-image/",
                {"product_id": self.product_id, "image": self.image_file((10, 10))},
                format="multipart",
            )
            self.assertEqual(accepted.status_code, 201)
        ninth = self.client.post(
            "/api/catalog/product-image/",
            {"product_id": self.product_id, "image": self.image_file()},
            format="multipart",
        )
        self.assertEqual(ninth.status_code, 409)

    def test_delete_removes_local_file_after_commit(self):
        uploaded = self.client.post(
            "/api/catalog/product-image/",
            {"product_id": self.product_id, "image": self.image_file()},
            format="multipart",
        )
        image = ProductImage.objects.get(pk=uploaded.data["id"])
        storage = image.image.storage
        name = image.image.name
        self.assertTrue(storage.exists(name))
        with self.captureOnCommitCallbacks(execute=True):
            deleted = self.client.delete(f"/api/catalog/product-image/{image.id}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(storage.exists(name))
