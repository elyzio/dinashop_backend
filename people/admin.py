from django.contrib import admin

from .models import Customer, Helper


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "phone", "normalized_phone", "address")
    ordering = ("name",)
    readonly_fields = ("id", "normalized_phone", "created_at", "updated_at")


@admin.register(Helper)
class HelperAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "phone", "normalized_phone")
    ordering = ("name",)
    readonly_fields = ("id", "normalized_phone", "created_at", "updated_at")
