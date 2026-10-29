from xml.etree import ElementTree

from django.conf import settings
from django.http import HttpResponse
from django.views import View

from storefront.selectors.catalog import public_sitemap_products


SITEMAP_NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
ElementTree.register_namespace("", SITEMAP_NAMESPACE)


def _add_url(root, *, location, last_modified=None, change_frequency=None, priority=None):
    entry = ElementTree.SubElement(root, f"{{{SITEMAP_NAMESPACE}}}url")
    ElementTree.SubElement(entry, f"{{{SITEMAP_NAMESPACE}}}loc").text = location
    if last_modified:
        ElementTree.SubElement(entry, f"{{{SITEMAP_NAMESPACE}}}lastmod").text = (
            last_modified.date().isoformat()
        )
    if change_frequency:
        ElementTree.SubElement(entry, f"{{{SITEMAP_NAMESPACE}}}changefreq").text = (
            change_frequency
        )
    if priority:
        ElementTree.SubElement(entry, f"{{{SITEMAP_NAMESPACE}}}priority").text = priority


class PublicSitemapView(View):
    def get(self, request):
        origin = settings.PUBLIC_STOREFRONT_URL
        root = ElementTree.Element(f"{{{SITEMAP_NAMESPACE}}}urlset")
        _add_url(
            root,
            location=f"{origin}/",
            change_frequency="daily",
            priority="1.0",
        )
        _add_url(
            root,
            location=f"{origin}/shop",
            change_frequency="daily",
            priority="0.9",
        )
        for product in public_sitemap_products().iterator():
            _add_url(
                root,
                location=f"{origin}/shop/{product.public_slug}",
                last_modified=product.updated_at,
                change_frequency="weekly",
                priority="0.8",
            )

        payload = ElementTree.tostring(
            root,
            encoding="utf-8",
            xml_declaration=True,
        )
        response = HttpResponse(payload, content_type="application/xml; charset=utf-8")
        response["Cache-Control"] = "public, max-age=300"
        return response
