import uuid

from rest_framework.exceptions import ValidationError


def parse_idempotency_key(request):
    raw_value = request.headers.get("Idempotency-Key")
    if not raw_value:
        raise ValidationError(
            {"idempotency_key": "The Idempotency-Key header is required."}
        )
    try:
        return uuid.UUID(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            {"idempotency_key": "The Idempotency-Key header must be a UUID."}
        ) from exc
