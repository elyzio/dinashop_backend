from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from inventory.models import InventoryBalance

from .models import (
    PriceHistory,
    Product,
    ProductCategory,
    ProductImage,
    ProductImageRendition,
    ProductOption,
    ProductOptionValue,
    ProductVariant,
    VariantOptionValue,
)


class ProductCategoryInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        rows = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data
            and not form.cleaned_data.get("DELETE", False)
            and form.cleaned_data.get("category") is not None
        ]
        if not rows:
            raise ValidationError("A product requires at least one category.")
        if sum(bool(row.get("is_primary")) for row in rows) != 1:
            raise ValidationError("Select exactly one primary category.")


class ProductCategoryInline(admin.TabularInline):
    model = ProductCategory
    formset = ProductCategoryInlineFormSet
    extra = 1
    autocomplete_fields = ("category",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image","alt_text","sort_order","width","height","file_size_bytes",)
    readonly_fields = ("width","height","file_size_bytes",)


class ProductOptionInline(admin.TabularInline):
    model = ProductOption
    extra = 0
    fields = ("name", "sort_order")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "public_slug", "brand", "visibility", "has_variants", "updated_at")
    list_filter = ("visibility", "has_variants", "categories")
    search_fields = ("name", "brand", "description", "variants__sku")
    ordering = ("name",)
    readonly_fields = ("id", "public_slug", "created_at", "updated_at")
    inlines = (ProductCategoryInline, ProductImageInline, ProductOptionInline)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("product", "category", "is_primary", "sort_order")
    list_filter = ("is_primary", "category")
    search_fields = ("product__name", "category__name")
    autocomplete_fields = ("product", "category")
    list_select_related = ("product", "category")


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "alt_text", "sort_order", "created_at")
    search_fields = ("product__name", "alt_text", "image")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
    readonly_fields = ("id", "created_at")


@admin.register(ProductImageRendition)
class ProductImageRenditionAdmin(admin.ModelAdmin):
    list_display = ("product_image", "kind", "width", "height", "file_size_bytes")
    list_filter = ("kind",)
    search_fields = ("product_image__product__name",)
    autocomplete_fields = ("product_image",)
    readonly_fields = ("id", "kind", "image", "width", "height", "file_size_bytes", "created_at")


@admin.register(ProductOption)
class ProductOptionAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "sort_order")
    search_fields = ("name", "product__name")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)


@admin.register(ProductOptionValue)
class ProductOptionValueAdmin(admin.ModelAdmin):
    list_display = ("value", "option", "product_name", "sort_order")
    search_fields = ("value", "option__name", "option__product__name")
    autocomplete_fields = ("option",)
    list_select_related = ("option", "option__product")

    @admin.display(ordering="option__product__name", description="Product")
    def product_name(self, obj):
        return obj.option.product.name


class VariantOptionValueInline(admin.TabularInline):
    model = VariantOptionValue
    extra = 0
    autocomplete_fields = ("option", "value")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "product",
        "selling_price",
        "sale_price",
        "is_active",
        "updated_at",
    )
    list_filter = ("is_active", "product")
    search_fields = ("sku", "product__name", "product__brand")
    autocomplete_fields = ("product",)
    list_select_related = ("product",)
    readonly_fields = ("id", "last_sale_at", "created_at", "updated_at")
    inlines = (VariantOptionValueInline,)

    @admin.display(ordering="selling_price_cents", description="Selling price")
    def selling_price(self, obj):
        return f"${obj.selling_price_cents / 100:,.2f}"

    @admin.display(ordering="sale_price_cents", description="Sale price")
    def sale_price(self, obj):
        if obj.sale_price_cents is None:
            return "—"
        return f"${obj.sale_price_cents / 100:,.2f}"

    def save_model(self, request, obj, form, change):
        previous = None
        if change:
            previous = ProductVariant.objects.get(pk=obj.pk)

        super().save_model(request, obj, form, change)
        InventoryBalance.objects.get_or_create(variant=obj)

        if previous is None or previous.selling_price_cents != obj.selling_price_cents:
            PriceHistory.objects.create(
                variant=obj,
                kind=PriceHistory.Kind.STANDARD,
                previous_cents=None if previous is None else previous.selling_price_cents,
                new_cents=obj.selling_price_cents,
                changed_by=request.user,
            )

        sale_changed = previous is None or any(
            (
                previous.sale_price_cents != obj.sale_price_cents,
                previous.sale_starts_at != obj.sale_starts_at,
                previous.sale_ends_at != obj.sale_ends_at,
            )
        )
        if sale_changed and obj.sale_price_cents is not None:
            PriceHistory.objects.create(
                variant=obj,
                kind=PriceHistory.Kind.SALE,
                previous_cents=None if previous is None else previous.sale_price_cents,
                new_cents=obj.sale_price_cents,
                sale_starts_at=obj.sale_starts_at,
                sale_ends_at=obj.sale_ends_at,
                changed_by=request.user,
            )


@admin.register(VariantOptionValue)
class VariantOptionValueAdmin(admin.ModelAdmin):
    list_display = ("variant", "option", "value")
    search_fields = ("variant__sku", "option__name", "value__value")
    autocomplete_fields = ("variant", "option", "value")
    list_select_related = ("variant", "option", "value")


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("variant", "kind", "previous_price", "new_price", "changed_by", "changed_at")
    list_filter = ("kind", "changed_at")
    search_fields = ("variant__sku", "variant__product__name", "changed_by__email")
    list_select_related = ("variant", "variant__product", "changed_by")
    readonly_fields = (
        "id",
        "variant",
        "kind",
        "previous_cents",
        "new_cents",
        "sale_starts_at",
        "sale_ends_at",
        "changed_by",
        "changed_at",
    )

    @admin.display(ordering="previous_cents", description="Previous")
    def previous_price(self, obj):
        return "—" if obj.previous_cents is None else f"${obj.previous_cents / 100:,.2f}"

    @admin.display(ordering="new_cents", description="New")
    def new_price(self, obj):
        return "—" if obj.new_cents is None else f"${obj.new_cents / 100:,.2f}"

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
