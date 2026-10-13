from django.contrib import admin

from .models import CodHandover, Payment, Refund, RefundLine


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "order",
        "amount",
        "method",
        "received_by_name",
        "occurred_at",
    )
    list_filter = ("method", "occurred_at")
    search_fields = ("receipt_number", "order__number", "external_reference", "received_by_name")
    list_select_related = ("order", "received_by")
    ordering = ("-occurred_at",)
    readonly_fields = tuple(field.name for field in Payment._meta.fields)

    @admin.display(ordering="amount_cents", description="Amount")
    def amount(self, obj):
        return f"${obj.amount_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RefundLineInline(admin.TabularInline):
    model = RefundLine
    extra = 0
    can_delete = False
    show_change_link = True
    readonly_fields = tuple(field.name for field in RefundLine._meta.fields if field.name != "refund")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "order",
        "credit",
        "cash_refund",
        "method",
        "processed_by_name",
        "created_at",
    )
    list_filter = ("method", "created_at")
    search_fields = ("number", "order__number", "reason", "processed_by_name")
    list_select_related = ("order", "payment", "processed_by")
    ordering = ("-created_at",)
    inlines = (RefundLineInline,)
    readonly_fields = tuple(field.name for field in Refund._meta.fields)

    @admin.display(ordering="credit_cents", description="Credit")
    def credit(self, obj):
        return f"${obj.credit_cents / 100:,.2f}"

    @admin.display(ordering="cash_refund_cents", description="Cash refund")
    def cash_refund(self, obj):
        return f"${obj.cash_refund_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RefundLine)
class RefundLineAdmin(admin.ModelAdmin):
    list_display = ("refund", "order_line", "quantity", "disposition", "amount")
    list_filter = ("disposition",)
    search_fields = ("refund__number", "order_line__order__number", "order_line__description")
    list_select_related = ("refund", "order_line", "order_line__order", "returned_variant")
    readonly_fields = tuple(field.name for field in RefundLine._meta.fields)

    @admin.display(ordering="amount_cents", description="Amount")
    def amount(self, obj):
        return f"${obj.amount_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CodHandover)
class CodHandoverAdmin(admin.ModelAdmin):
    list_display = ("handed_over_at", "helper", "order", "amount", "recorded_by")
    list_filter = ("handed_over_at", "helper")
    search_fields = ("helper__name", "order__number")
    list_select_related = ("helper", "order", "recorded_by")
    ordering = ("-handed_over_at",)
    readonly_fields = tuple(field.name for field in CodHandover._meta.fields)

    @admin.display(ordering="amount_cents", description="Amount")
    def amount(self, obj):
        return f"${obj.amount_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
