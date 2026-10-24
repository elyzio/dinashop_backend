from django.contrib import admin

from .models import AuditEvent, BusinessSettings, Category, DocumentSequence


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "status", "sort_order", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "slug", "parent__name")
    ordering = ("sort_order", "name")
    autocomplete_fields = ("parent",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(BusinessSettings)
class BusinessSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "business_name",
        "whatsapp_phone",
        "currency",
        "timezone",
        "low_stock_threshold",
        "updated_at",
    )
    readonly_fields = ("id", "key", "created_at", "updated_at")

    def has_add_permission(self, request):
        return not BusinessSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DocumentSequence)
class DocumentSequenceAdmin(admin.ModelAdmin):
    list_display = ("key", "prefix", "last_value", "updated_at")
    search_fields = ("key", "prefix")

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ("last_value", "updated_at")
        return ("key", "prefix", "last_value", "updated_at")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "entity_type", "entity_id")
    list_filter = ("action", "entity_type", "created_at")
    search_fields = ("action", "entity_type", "entity_id", "actor__email")
    list_select_related = ("actor",)
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "actor",
        "action",
        "entity_type",
        "entity_id",
        "before",
        "after",
        "request_id",
        "ip_address",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
