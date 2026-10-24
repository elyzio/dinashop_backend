from django.core.management.base import BaseCommand, CommandError

from catalog.models import ProductImage
from catalog.services.image import regenerate_product_image_renditions


class Command(BaseCommand):
    help = "Create responsive WebP renditions for existing product images."

    def add_arguments(self, parser):
        parser.add_argument("--product-id")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        queryset = ProductImage.objects.exclude(image="").prefetch_related("renditions")
        if options["product_id"]:
            queryset = queryset.filter(product_id=options["product_id"])
        if options["limit"]:
            queryset = queryset[: options["limit"]]

        processed = 0
        for image in queryset:
            if not options["force"] and image.renditions.count() == 3:
                continue
            try:
                regenerate_product_image_renditions(image=image)
            except Exception as exc:
                raise CommandError(f"Could not process {image.id}: {exc}") from exc
            processed += 1
            self.stdout.write(f"Generated renditions for {image.id}")
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} product image(s)."))
