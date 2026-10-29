from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings


@override_settings(PUBLIC_STOREFRONT_URL="https://shop.example.com")
class PublicSitemapViewTests(SimpleTestCase):
    @patch("storefront.views.sitemap.public_sitemap_products")
    def test_public_sitemap_is_valid_xml_with_canonical_product_urls(self, products):
        products.return_value.iterator.return_value = iter(
            [
                SimpleNamespace(
                    public_slug="classic-shirt",
                    updated_at=datetime(2026, 10, 29, tzinfo=timezone.utc),
                )
            ]
        )

        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml; charset=utf-8")
        body = response.content.decode()
        self.assertIn("<urlset xmlns=", body)
        self.assertIn("https://shop.example.com/shop/classic-shirt</loc>", body)
        self.assertIn("<lastmod>2026-10-29</lastmod>", body)
        self.assertEqual(response["Cache-Control"], "public, max-age=300")
