from django.contrib import admin

from .models import DeliveryJob


@admin.register(DeliveryJob)
class DeliveryJobAdmin(admin.ModelAdmin):
    list_display = (
        "order",
        "helper",
        "status",
        "fee",
        "fuel",
        "status_changed_at",
    )
    list_filter = ("status", "helper", "status_changed_at")
    search_fields = ("order__number", "helper__name", "failure_reason")
    list_select_related = ("order", "helper", "created_by", "updated_by")
    ordering = ("-created_at",)
    readonly_fields = tuple(field.name for field in DeliveryJob._meta.fields)

    @admin.display(ordering="fee_cents", description="Fee")
    def fee(self, obj):
        return f"${obj.fee_cents / 100:,.2f}"

    @admin.display(ordering="fuel_cents", description="Fuel")
    def fuel(self, obj):
        return f"${obj.fuel_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
