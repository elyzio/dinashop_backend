from collections.abc import Mapping

from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.views import exception_handler


class ConflictError(APIException):
    status_code = 409
    default_detail = "The request conflicts with the current resource state."
    default_code = "conflict"


class PayloadTooLargeError(APIException):
    status_code = 413
    default_detail = "The uploaded file is too large."
    default_code = "payload_too_large"


def _normalise_fields(data):
    if not isinstance(data, Mapping):
        return None
    fields = {}
    for key, value in data.items():
        if key == "detail":
            continue
        if isinstance(value, Mapping):
            fields[key] = value
        elif isinstance(value, (list, tuple)):
            fields[key] = [str(item) for item in value]
        else:
            fields[key] = [str(value)]
    return fields or None


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, ValidationError):
        code = "validation_error"
        message = "The request contains invalid values."
    elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        code = "authentication_required"
        message = "Valid authentication credentials are required."
    elif isinstance(exc, PermissionDenied):
        code = "permission_denied"
        message = "You do not have permission to perform this action."
    elif isinstance(exc, Throttled):
        code = "rate_limited"
        message = "Too many requests. Try again later."
    else:
        code = getattr(exc, "default_code", None) or "request_error"
        detail = getattr(exc, "detail", None)
        if hasattr(detail, "code"):
            code = detail.code
        message = str(detail or "The request could not be completed.")

    payload = {"code": str(code), "message": message}
    fields = _normalise_fields(response.data)
    if fields:
        payload["fields"] = fields
    response.data = {"error": payload}
    return response
