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