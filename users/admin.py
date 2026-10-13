from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import NotificationReceipt, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "last_login",
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal information", {"fields": ("first_name", "last_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


@admin.register(NotificationReceipt)
class NotificationReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "notification_id",
        "user",
        "fingerprint",
        "read_at",
        "dismissed_at",
        "updated_at",
    )
    list_filter = ("read_at", "dismissed_at")
    search_fields = ("notification_id", "fingerprint", "user__email")
    list_select_related = ("user",)
    readonly_fields = (
        "id",
        "user",
        "notification_id",
        "fingerprint",
        "read_at",
        "dismissed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
