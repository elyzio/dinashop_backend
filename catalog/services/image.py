import io
import uuid
import warnings

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

from catalog.models import Product, ProductImage, ProductImageRendition
from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError, PayloadTooLargeError


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 36_000_000
MAX_DIMENSION = 1600
WEBP_QUALITY = 82
MAX_IMAGES_PER_PRODUCT = 8
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
RENDITION_DIMENSIONS = {
    ProductImageRendition.Kind.THUMBNAIL: 160,
    ProductImageRendition.Kind.CARD: 640,
    ProductImageRendition.Kind.DETAIL: 1280,
}


def _encode_webp(image, maximum_dimension):
    rendition = image.copy()
    rendition.thumbnail((maximum_dimension, maximum_dimension), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    rendition.save(output, format="WEBP", quality=WEBP_QUALITY, method=6)
    payload = output.getvalue()
    return payload, rendition.width, rendition.height


def _process_image(uploaded_file):
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise PayloadTooLargeError("Product images cannot exceed 5 MB.")
    try:
        uploaded_file.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(uploaded_file) as probe:
                image_format = probe.format
                width, height = probe.size
                probe.verify()
        if image_format not in ALLOWED_FORMATS:
            raise ValidationError({"image": "Upload a JPEG, PNG, or WebP image."})
        if width * height > MAX_PIXELS:
            raise ValidationError({"image": "Image resolution cannot exceed 36 megapixels."})

        uploaded_file.seek(0)
        with Image.open(uploaded_file) as source:
            image = ImageOps.exif_transpose(source)
            has_alpha = image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            )
            image = image.convert("RGBA" if has_alpha else "RGB")
            source_payload, width, height = _encode_webp(image, MAX_DIMENSION)
            renditions = {
                kind: _encode_webp(image, maximum_dimension)
                for kind, maximum_dimension in RENDITION_DIMENSIONS.items()
            }
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError({"image": "Image resolution is unsafe."})
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationError({"image": "The uploaded file is not a valid image."}) from exc
    return {
        "source": (source_payload, width, height),
        "renditions": renditions,
    }


def create_product_image(*, product, uploaded_file, alt_text="", sort_order=None, actor, request=None):
    processed = _process_image(uploaded_file)
    source_payload, width, height = processed["source"]
    image = None
    stored_names = []
    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product.pk)
            image_count = product.images.count()
            if image_count >= MAX_IMAGES_PER_PRODUCT:
                raise ConflictError(
                    "A product can have at most eight images.",
                    code="image_limit_reached",
                )
            if sort_order is None:
                sort_order = image_count
            image = ProductImage(
                product=product,
                alt_text=alt_text.strip(),
                sort_order=sort_order,
                width=width,
                height=height,
                file_size_bytes=len(source_payload),
            )
            image.image.save(
                f"{uuid.uuid4().hex}.webp",
                ContentFile(source_payload),
                save=False,
            )
            stored_names.append((image.image.storage, image.image.name))
            image.save()
            for kind, (payload, rendition_width, rendition_height) in processed["renditions"].items():
                rendition = ProductImageRendition(
                    product_image=image,
                    kind=kind,
                    width=rendition_width,
                    height=rendition_height,
                    file_size_bytes=len(payload),
                )
                rendition.image.save(
                    f"{kind}-{uuid.uuid4().hex}.webp",
                    ContentFile(payload),
                    save=False,
                )
                stored_names.append((rendition.image.storage, rendition.image.name))
                rendition.save()
            record_audit_event(
                actor=actor,
                action="product_image.created",
                entity_type="catalog.ProductImage",
                entity_id=image.id,
                after={
                    "product_id": str(product.id),
                    "width": width,
                    "height": height,
                    "file_size_bytes": len(source_payload),
                },
                request=request,
            )
    except Exception:
        for storage, stored_name in stored_names:
            storage.delete(stored_name)
        raise
    return image


def regenerate_product_image_renditions(*, image):
    """Generate missing/replaced responsive files for an existing source image.

    This intentionally has no audit event: it is a derived-file maintenance task.
    """
    processed = _process_image(image.image)
    existing = {item.kind: item for item in image.renditions.all()}
    old_files = []
    new_files = []
    try:
        with transaction.atomic():
            image = ProductImage.objects.select_for_update().get(pk=image.pk)
            for kind, (payload, width, height) in processed["renditions"].items():
                rendition = existing.get(kind) or ProductImageRendition(
                    product_image=image,
                    kind=kind,
                )
                if rendition.pk and rendition.image:
                    old_files.append((rendition.image.storage, rendition.image.name))
                rendition.width = width
                rendition.height = height
                rendition.file_size_bytes = len(payload)
                rendition.image.save(
                    f"{kind}-{uuid.uuid4().hex}.webp",
                    ContentFile(payload),
                    save=False,
                )
                new_files.append((rendition.image.storage, rendition.image.name))
                rendition.save()
            transaction.on_commit(
                lambda: [storage.delete(name) for storage, name in old_files]
            )
    except Exception:
        for storage, name in new_files:
            storage.delete(name)
        raise


@transaction.atomic
def delete_product_image(*, image, actor, request=None):
    image = ProductImage.objects.select_for_update().get(pk=image.pk)
    files = [(image.image.storage, image.image.name)]
    files.extend((rendition.image.storage, rendition.image.name) for rendition in image.renditions.all())
    image_id = image.id
    product_id = image.product_id
    image.delete()
    transaction.on_commit(lambda: [storage.delete(name) for storage, name in files])
    record_audit_event(
        actor=actor,
        action="product_image.deleted",
        entity_type="catalog.ProductImage",
        entity_id=image_id,
        before={"product_id": str(product_id), "storage_names": [name for _, name in files]},
        request=request,
    )


@transaction.atomic
def update_product_image_metadata(*, image, data, actor, request=None):
    image = ProductImage.objects.select_for_update().get(pk=image.pk)
    before = {"alt_text": image.alt_text, "sort_order": image.sort_order}
    if "alt_text" in data:
        image.alt_text = data["alt_text"].strip()
    if "sort_order" in data:
        image.sort_order = data["sort_order"]
    image.save(update_fields=("alt_text", "sort_order"))
    record_audit_event(
        actor=actor,
        action="product_image.updated",
        entity_type="catalog.ProductImage",
        entity_id=image.id,
        before=before,
        after={"alt_text": image.alt_text, "sort_order": image.sort_order},
        request=request,
    )
    return image


@transaction.atomic
def reorder_product_images(*, product, image_ids, actor, request=None):
    product = Product.objects.select_for_update().get(pk=product.pk)
    images = list(ProductImage.objects.select_for_update().filter(product=product))
    existing_ids = {image.id for image in images}
    if set(image_ids) != existing_ids or len(image_ids) != len(images):
        raise ValidationError(
            {"image_ids": "Provide every image ID for this product exactly once."}
        )
    positions = {image_id: index for index, image_id in enumerate(image_ids)}
    for image in images:
        image.sort_order = positions[image.id]
    ProductImage.objects.bulk_update(images, ("sort_order",))
    record_audit_event(
        actor=actor,
        action="product_image.reordered",
        entity_type="catalog.Product",
        entity_id=product.id,
        after={"image_ids": [str(item) for item in image_ids]},
        request=request,
    )
    return sorted(images, key=lambda item: item.sort_order)
