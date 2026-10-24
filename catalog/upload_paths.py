from pathlib import Path
from uuid import uuid4


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def product_image_upload_path(instance, filename):
    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        extension = ".bin"

    return (
        f"products/{instance.product_id}/"
        f"{uuid4().hex}{extension}"
    )


def product_image_rendition_upload_path(instance, filename):
    """Store generated files beside, but separately from, the source image."""
    return (
        f"products/{instance.product_image.product_id}/renditions/"
        f"{instance.product_image_id}/{instance.kind}-{uuid4().hex}.webp"
    )
