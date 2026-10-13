import io
import tempfile
import uuid

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from catalog.models import PriceHistory, Product, ProductImage, ProductVariant
from custom.models import Category
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
