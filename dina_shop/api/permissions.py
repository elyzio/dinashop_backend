from rest_framework.permissions import BasePermission


class IsAuthenticatedOwner(BasePermission):
    """V1 permission: every active authenticated account is an owner account."""

    message = "An active owner account is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
        )
