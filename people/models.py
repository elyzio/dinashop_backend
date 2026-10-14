import re
import uuid

from django.db import models
from django.db.models import Q


def normalize_phone(value: str) -> str:
    value = value.strip()
    prefix = "+" if value.startswith("+") else ""
    return prefix + re.sub(r"\D", "", value)


class Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True)
    normalized_phone = models.CharField(max_length=40, blank=True, db_index=True)
    address = models.TextField(blank=True)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_walk_in = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=("is_walk_in",),
                condition=Q(is_walk_in=True),
                name="uq_single_walk_in_customer",
            )
        ]
        indexes = [models.Index(fields=["is_active", "name"])]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.normalized_phone = normalize_phone(self.phone) if self.phone else ""
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Helper(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=160)
    phone = models.CharField(max_length=40, blank=True)
    normalized_phone = models.CharField(max_length=40, blank=True, db_index=True)
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["is_active", "name"])]

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.normalized_phone = normalize_phone(self.phone) if self.phone else ""
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
