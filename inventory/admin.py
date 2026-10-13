from django.contrib import admin

from .models import InventoryBalance, StockMovement, StockReservation


@admin.register(InventoryBalance)
class InventoryBalanceAdmin(admin.ModelAdmin):
    list_display = (
        "variant",
        "in_hand",
        "promised",
        "available_quantity",
        "landed_cost",
        "updated_at",
    )
    search_fields = ("variant__sku", "variant__product__name")
    list_select_related = ("variant", "variant__product")
    readonly_fields = tuple(field.name for field in InventoryBalance._meta.fields)

    @admin.display(description="Available")
    def available_quantity(self, obj):
        return obj.available

    @admin.display(ordering="last_landed_cost_cents", description="Last landed cost")
    def landed_cost(self, obj):
        if obj.last_landed_cost_cents is None:
            return "—"
        return f"${obj.last_landed_cost_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ("order_line", "variant", "quantity", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("order_line__order__number", "variant__sku")
    list_select_related = ("order_line", "order_line__order", "variant")
    readonly_fields = tuple(field.name for field in StockReservation._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "variant",
        "movement_type",
        "quantity_delta",
        "reference",
        "order",
        "recorded_by",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = ("variant__sku", "variant__product__name", "reference", "order__number")
    list_select_related = ("variant", "variant__product", "order", "recorded_by")
    ordering = ("-created_at",)
    readonly_fields = tuple(field.name for field in StockMovement._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
