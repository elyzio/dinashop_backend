from django.contrib import admin

from .models import Order, OrderLine


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    can_delete = False
    show_change_link = True
    readonly_fields = (
        "kind",
        "variant",
        "product_name",
        "variant_description",
        "sku",
        "description",
        "quantity",
        "unit_price_cents",
        "estimated_tax_cents",
        "actual_tax_cents",
        "landed_cost_cents",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "customer",
        "status",
        "special_status",
        "delivery_method",
        "cod",
        "created_at",
    )
    list_filter = ("status", "special_status", "delivery_method", "cod", "created_at")
    search_fields = (
        "number",
        "customer__name",
        "customer__phone",
        "customer_name",
        "customer_phone",
        "lines__description",
        "lines__sku",
    )
    list_select_related = ("customer", "created_by")
    ordering = ("-created_at",)
    inlines = (OrderLineInline,)
    readonly_fields = tuple(field.name for field in Order._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ("order", "kind", "description", "quantity", "unit_price", "sku")
    list_filter = ("kind", "created_at")
    search_fields = ("order__number", "description", "product_name", "sku")
    list_select_related = ("order", "variant")
    readonly_fields = tuple(field.name for field in OrderLine._meta.fields)

    @admin.display(ordering="unit_price_cents", description="Unit price")
    def unit_price(self, obj):
        return f"${obj.unit_price_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
