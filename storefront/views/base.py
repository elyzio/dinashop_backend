from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle


class PublicStorefrontViewMixin:
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_catalog"
