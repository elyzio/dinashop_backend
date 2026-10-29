from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient
from django.test import TestCase

from catalog.models import (
    Product,
    ProductCategory,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    VariantOptionValue,
)
from custom.models import BusinessSettings, Category
from inventory.models import InventoryBalance
from users.models import User


class PublicStorefrontApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            email="storefront-owner@example.com", password="safe-pass"
        )
        self.clothing = Category.objects.create(name="Clothing", slug="clothing")
        self.shirts = Category.objects.create(
            name="Shirts", slug="shirts", parent=self.clothing
        )
        self.special = Category.objects.get(slug="special-order-stock")
        self.special.status = Category.Status.ACTIVE
        self.special.save(update_fields=["status"])
        self.settings = BusinessSettings.objects.get(key="default")
        self.settings.business_name = "Dina Shop"
        self.settings.currency = "USD"
        self.settings.phone = "+81 3 0000 0000"
        self.settings.whatsapp_phone = "+81 (90) 1234-5678"
        self.settings.email = "contact@example.com"
        self.settings.latitude = "-8.556856"
        self.settings.longitude = "125.560314"
        self.settings.save()
        self.available = self.make_product(
            "Classic T-Shirt", "classic-t-shirt", self.shirts, available=3, with_option=True
        )
        self.sold_out = self.make_product(
            "Sold Out Shirt", "sold-out-shirt", self.shirts, available=0
        )
        self.hidden = self.make_product(
            "Private Shirt", "private-shirt", self.shirts, available=2, visibility="hidden"
        )
        self.special_product = self.make_product(
            "Special Order Item", "special-order-item", self.special, available=2
        )

    def make_product(
        self, name, slug, category, *, available, visibility="active", with_option=False
    ):
        product = Product.objects.create(
            name=name,
            public_slug=slug,
            visibility=visibility,
            has_variants=with_option,
        )
        ProductCategory.objects.create(product=product, category=category, is_primary=True)
        variant = ProductVariant.objects.create(
            product=product,
            sku=f"{slug.upper()}-SKU",
            selling_price_cents=2500,
            sale_price_cents=2000 if slug == "classic-t-shirt" else None,
            sale_starts_at=timezone.now() - timedelta(days=1) if slug == "classic-t-shirt" else None,
            sale_ends_at=timezone.now() + timedelta(days=1) if slug == "classic-t-shirt" else None,
        )
        InventoryBalance.objects.create(variant=variant, in_hand=available)
        if with_option:
            option = ProductOption.objects.create(product=product, name="Color")
            value = ProductOptionValue.objects.create(option=option, value="Black")
            VariantOptionValue.objects.create(variant=variant, option=option, value=value)
        return product

    def test_public_list_is_anonymous_and_hides_operational_fields(self):
        response = self.client.get("/api/public/product/")
        self.assertEqual(response.status_code, 200, response.data)
        names = {item["name"] for item in response.data["results"]}
        self.assertEqual(names, {"Classic T-Shirt", "Sold Out Shirt"})
        card = next(item for item in response.data["results"] if item["slug"] == "classic-t-shirt")
        self.assertEqual(card["from_price_cents"], 2000)
        self.assertTrue(card["has_active_sale"])
        self.assertEqual(card["availability"], "available")
        self.assertNotIn("id", card)
        self.assertNotIn("sku", card)
        self.assertNotIn("available_quantity", card)

        owner_only = self.client.get("/api/catalog/product/")
        self.assertEqual(owner_only.status_code, 401, owner_only.data)

    def test_category_filter_search_ordering_and_unknown_category(self):
        category = self.client.get("/api/public/category/")
        self.assertEqual(category.status_code, 200, category.data)
        categories = {item["slug"]: item for item in category.data}
        self.assertEqual(categories["clothing"]["product_count"], 2)
        self.assertEqual(categories["shirts"]["product_count"], 2)
        self.assertNotIn("special-order-stock", categories)

        filtered = self.client.get("/api/public/product/?category=clothing&search=classic")
        self.assertEqual(filtered.status_code, 200, filtered.data)
        self.assertEqual(filtered.data["count"], 1)
        self.assertEqual(filtered.data["results"][0]["slug"], "classic-t-shirt")
        self.assertEqual(
            self.client.get("/api/public/product/?category=unknown").status_code, 404
        )
        self.assertEqual(
            self.client.get("/api/public/product/?ordering=inventory").status_code, 400
        )

    def test_public_detail_exposes_variant_selection_not_sku_or_stock(self):
        response = self.client.get("/api/public/product/classic-t-shirt/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["variants"][0]["options"], {"Color": "Black"})
        self.assertEqual(response.data["variants"][0]["price_cents"], 2000)
        self.assertEqual(response.data["variants"][0]["sale_price_cents"], 2000)
        self.assertEqual(response.data["variants"][0]["availability"], "available")
        self.assertEqual(response.data["request_url"].split("?", 1)[0], "https://wa.me/819012345678")
        self.assertNotIn("sku", response.data["variants"][0])
        self.assertNotIn("in_hand", response.data["variants"][0])
        self.assertEqual(self.client.get("/api/public/product/missing/").status_code, 404)

    def test_storefront_uses_safe_business_fields_and_whatsapp_is_optional(self):
        response = self.client.get("/api/public/storefront/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["business_name"], "Dina Shop")
        self.assertEqual(response.data["whatsapp_url"], "https://wa.me/819012345678")
        self.assertEqual(response.data["email"], "contact@example.com")
        self.assertEqual(
            response.data["location_url"],
            "https://www.google.com/maps/search/?api=1&query=-8.556856,125.560314",
        )
        self.assertNotIn("registration_id", response.data)
        self.assertNotIn("latitude", response.data)
        self.assertNotIn("longitude", response.data)

        self.settings.whatsapp_phone = ""
        self.settings.latitude = None
        self.settings.longitude = None
        self.settings.save(update_fields=["whatsapp_phone", "latitude", "longitude"])
        storefront = self.client.get("/api/public/storefront/")
        self.assertIsNone(storefront.data["location_url"])
        detail = self.client.get("/api/public/product/sold-out-shirt/")
        self.assertEqual(detail.data["availability"], "sold_out")
        self.assertIsNone(detail.data["request_url"])

    def test_public_slug_is_stable_when_product_is_renamed(self):
        self.available.name = "Renamed public shirt"
        self.available.save(update_fields=["name"])
        self.available.refresh_from_db()
        self.assertEqual(self.available.public_slug, "classic-t-shirt")

    def test_sitemap_contains_only_public_storefront_products(self):
        with self.settings(PUBLIC_STOREFRONT_URL="https://shop.example.com"):
            response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        body = response.content.decode()
        self.assertIn("https://shop.example.com/</loc>", body)
        self.assertIn("https://shop.example.com/shop</loc>", body)
        self.assertIn(
            "https://shop.example.com/shop/classic-t-shirt</loc>", body
        )
        self.assertIn(
            "https://shop.example.com/shop/sold-out-shirt</loc>", body
        )
        self.assertNotIn("private-shirt", body)
        self.assertNotIn("special-order-item", body)

    def test_admin_or_management_product_creation_receives_a_public_slug(self):
        product = Product.objects.create(name="New Public Product")
        self.assertEqual(product.public_slug, "new-public-product")
        duplicate = Product.objects.create(name="New Public Product")
        self.assertEqual(duplicate.public_slug, "new-public-product-2")
